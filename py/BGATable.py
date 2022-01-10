import re
import json
import ast
import time
import threading
from BGANotifications import BGANotifications

from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1

class BGATable:
    """ Manages the connection to a specific "table" or game at
    BGA. """

    # After three minutes, we'll remove inactive tables from the list.
    inactive_table_timeout = 3 * 60

    def __init__(self, bga, table_id):
        print("Creating %s for %s" % (self.__class__.__name__, table_id))
        assert(isinstance(table_id, int))
        self.bga = bga
        self.table_id = table_id
        self.table_infos = None
        self.gameserver = None
        self.game_name = None
        self.last_packet_id = 0
        self.game_state = {}
        self.game_inactive = False
        self.last_message = 0

        self.accepted_invite = False
        self.accepted_start = False

        self.gs_notification = None
        self.gs_socketio_url = None
        self.gs_socketio_path = None

        self.gen_notification = None

        self.lock = threading.RLock()

        self.notifications = BGANotifications(self.bga, name = str(self.table_id), auto_restart = True)

        # Now we create our own thread to dispatch our table-specific
        # notifications.
        self.shutdown = False
        thread_name = 'Table thread %s' % (self.table_id)
        self.table_thread = threading.Thread(target = self.table_thread_main, name = thread_name)
        self.table_thread.start()

    def cleanup(self):
        self.shutdown = True
        self.table_thread.join()

        self.notifications.cleanup()
        self.gs_notification = None
        self.gen_notification = None

    def table_thread_main(self):
        """ This is the primary thread that serves the table. """

        self.setup_gen_notifications()
        self.fetch_table_infos()

        while not self.shutdown:
            # Check for active notifications
            self.notifications.dispatch(block = True, timeout = 1)

            # We should also poll from time to time, in case a message
            # got dropped.
            self.poll()

    def is_table_thread(self):
        """ Returns True if we are currently running in the table
        thread, False otherwise.  A sanity check. """
        return threading.current_thread() == self.table_thread

    def is_main_thread(self):
        """ Returns True if we are currently running in the main
        thread, False otherwise.  A sanity check. """
        return threading.current_thread() == self.bga.main_thread

    def setup_gen_notifications(self):
        """ Starts listening for the general table notifications that
        are managed by the main BGA server.  This includes requests to
        abandon the game, and whatnot.  We can listen to this
        immediately, as soon as we know the table_id. """

        assert(self.is_table_thread())

        self.gen_notification = self.notifications.create_notification_session(
            message_callback = self.__gs_notification)

        self.gen_notification.subscribe_channels(
            "/table/t%s" % (self.table_id),
            )

    def setup_gs_notifications(self):
        """ Starts listening for the in-game notifications that are
        sent directly from the specific gameserver this table has been
        assigned to.  We can call this as soon as we establish an
        actual gameserver, not '0'.  Called only in the table thread. """

        assert(self.is_table_thread())

        print("Got gameserver %s, setting up notifications" % (self.gameserver))
        self.read_gameui_data()

        self.gs_notification = self.notifications.create_notification_session(
            message_callback = self.__gs_notification,
            socketio_url = self.gs_socketio_url,
            socketio_path = self.gs_socketio_path)

        self.gs_notification.subscribe_channels(
            "/table/t%s" % (self.table_id),

            # This channel seems to be for spectator notifications, we
            # don't care about that.
            #"/table/ts%s" % (self.table_id),
            )

        self.fetch_notification_history()
        self.consider_turn()

    def fetch_table_infos(self):
        """ Updates self.table_infos with the most recent data about
        this game from BGA.  This is the top-level information about
        the game and how it is hosted.

        This is called only in the table thread. """

        assert(self.is_table_thread())

        tableinfo_url = 'https://boardgamearena.com/table/table/tableinfos.html'
        tableinfo_params = {
            'id' : self.table_id,
            }

        r = self.bga.session.get(tableinfo_url, params = tableinfo_params)
        dict = json.loads(r.text)
        table_infos = dict['data']
        self.__apply_table_infos(table_infos)

    def read_gameui_data(self):
        """ Updates the relevant data passed to the Javascript object
        gameui, by extracting it from the Javascript code loaded with
        this particular table's page.  This data is only available
        once we have been told a specific gameserver number, other
        than '0' which means it hasn't been assigned yet. """

        assert(self.is_table_thread())

        assert(self.gameserver and self.gameserver != '0')

        # Go to the web page hosted for this table on the assigned
        # gameserver.
        table_url = 'https://boardgamearena.com/%s/%s' % (self.gameserver, self.game_name)
        table_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(table_url, params = table_params)

        # Now look for gameui.gs_socketio_url and
        # gameui.gs_socketio_path in that returned page.
        m = re.search('[ \t]+gameui[.]gs_socketio_url=(.*);', r.text)
        if m is None:
            message = "gs_socketio_url not found"
            raise RuntimeError(message)

        self.gs_socketio_url = ast.literal_eval(m.group(1))

        m = re.search('[ \t]+gameui[.]gs_socketio_path=(.*);', r.text)
        if m is None:
            message = "gs_socketio_path not found"
            raise RuntimeError(message)

        self.gs_socketio_path = ast.literal_eval(m.group(1))

        # Also look for gameui.decision, which might have a request to
        # abandon the game or whatever.
        m = re.search('[ \t]+gameui[.]decision=(.*);', r.text)
        if m is not None:
            args = json.loads(m.group(1))
            self.consider_table_decision(args)

    def fetch_notification_history(self):
        assert(self.is_table_thread())

        # TODO: Is the game_name really repeated, or does the second
        # name come from another source?
        history_url = 'https://boardgamearena.com/%s/%s/%s/notificationHistory.html' % (self.gameserver, self.game_name, self.game_name)
        history_params = {
            'table' : self.table_id,
            'from' : self.last_packet_id,
            'privateinc' : 1,
            'history' : 1,
            }

        r = self.bga.session.get(history_url, params = history_params)
        dict = json.loads(r.text)
        past_notifications = dict['data']['data']

        print("Found %s past notifications" % (len(past_notifications)))
        for bgamsg_data in past_notifications:
            channel = bgamsg_data['channel']
            self.__gs_notification(channel, bgamsg_data, False)

    def __apply_table_infos(self, table_infos):
        """ A new table_infos dictionary has been acquired.  Store it,
        and deal with whatever it says.  This is called only in the
        table thread. """

        assert(self.is_table_thread())

        self.table_infos = table_infos
        self.gameserver = self.table_infos['gameserver']
        self.game_name = self.table_infos['game_name']

        # Initially, BGA assigns us a gameserver of '0', which means
        # no particular server has been assigned yet.  When it
        # eventually does assign the table to a gameserver, it will
        # replace this '0' with a non-zero digit.
        assert(self.gameserver)
        #print("self.gameserver = %s" % (self.gameserver))

        if not self.gs_notification and self.gameserver != '0':
            # If we have a real gameserver now, then sign up for
            # in-game notifications.
            self.setup_gs_notifications()

        self.update_table_infos()

    def update_table_infos(self):
        """ Called whenever self.table_infos has been updated.  This
        is called only in the table thread. """

        assert(self.is_table_thread())

        self.last_message = time.time()

        if [int(id) for id in self.table_infos['players']] == [int(self.bga.user_id)]:
            # If we're the only player in the game, abandon it.
            self.abandon_game()
            return

        status = self.table_infos['status']
        print("updated table_info for %s, status = %s" % (self.table_id, status))
        if status == 'open':
            me_info = self.table_infos['players'].get(str(self.bga.user_id), None)
            table_status = me_info and me_info['table_status']
            if table_status == 'setup':
                # We're not in the game yet.
                pass
            elif table_status == 'expected':
                print("expected")
                # Let's wait just a moment before accepting the
                # invite, to help avoid a BGA race condition on the
                # remote BGA clients.
                time.sleep(1)
                self.accept_invite()
            elif table_status == 'play':
                print("table_status is play")
                # We're probably waiting for the "start" button to be
                # pressed.
            else:
                print("Unhandled table status %s" % (table_status))
        elif status == 'setup':
            print("setup")
            # In this case we must have accepted the invite previously.
            self.accepted_invite = True
        elif status == 'play':
            print("Game is actively playing.")
            # In this case we must have accepted the start previously.
            self.accepted_invite = True
            self.accepted_start = True
        elif status == 'asyncinit':
            # We won't accept a "turn-based" game.
            print("Don't want to play async game")
            self.abandon_game()
        elif status == 'finished':
            print("Game is finished.")
            self.game_inactive = True
        else:
            print("Unhandled game status %s" % (status))

    def accept_invite(self):
        """ Called in the table thread. """

        assert(self.is_table_thread())

        join_url = 'https://boardgamearena.com/table/table/joingame.html'
        join_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(join_url, params = join_params)
        assert(r.status_code == 200)
        dict = json.loads(r.text)
        if int(dict['status']):
            print("Accepted invite")
        else:
            print("Unexpected result from %s" % (r.url))
            print(dict)

        self.accepted_invite = True

    def accept_start(self):
        """ Called in the main thread (not the table thread) by the
        parent class. """

        assert(self.is_main_thread())

        accept_url = 'https://boardgamearena.com/table/table/acceptGameStart.html'
        accept_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(accept_url, params = accept_params)
        assert(r.status_code == 200)
        dict = json.loads(r.text)
        if int(dict['status']):
            print("Accepted start")
        else:
            print("Unexpected result from %s" % (r.url))
            print(dict)

        self.accepted_invite = True
        self.accepted_start = True

    def send_myturnack(self):
        """ Sends an explicit message to acknowledge that we have seen
        that it's our turn. """

        # I don't think this is actually needed?  The actual BGA
        # client sends this from time to time, but we never call this
        # and it doesn't seem to mind.  OK.
        wakeup_url = 'https://boardgamearena.com/%s/%s/%s/wakeup.html' % (self.gameserver, self.game_name, self.game_name)
        wakeup_params = {
            'myturnack' : 'true',
            'table' : self.table_id,
            }
        r = self.bga.session.get(wakeup_url, params = wakeup_params)
        assert(r.status_code == 200)
        print(r.text)

    def __gs_notification(self, channel, bgamsg_data, live):
        """ A notification is received on the named channel from the
        gameserver that hosts this table.  This method is called only
        on the table thread. """

        assert(self.is_table_thread())

        data = bgamsg_data['data']
        packet_id = int(bgamsg_data.get('packet_id', 0))
        #print("gs notification on %s, packet_id %s" % (channel, packet_id))

        if channel == '/table/t%s' % (self.table_id):
            if packet_id == 0 or packet_id > self.last_packet_id:
                if packet_id > self.last_packet_id:
                    self.last_packet_id = packet_id
                for data_dict in data:
                    notification_type = data_dict['type']
                    self.table_notification(notification_type, data_dict, live)
            else:
                print("Ignoring out-of-sequence notification %s: %s" % (packet_id, data))
        else:
            print("Unhandled gs notification on %s: %s" % (channel, data))

    def __gen_notification(self, channel, bgamsg_data, live):
        """ A notification is received on the named channel from the
        main BGA server.  This method is called only on the table
        thread. """

        assert(self.is_table_thread())

        data = bgamsg_data['data']
        print("gen notification on %s" % (channel))

        if channel == '/table/t%s' % (self.table_id):
            for data_dict in data:
                notification_type = data_dict['type']
                self.table_notification(notification_type, data_dict, live)
        else:
            print("Unhandled gen notification on %s: %s" % (channel, data))

    def consider_table_decision(self, args):
        """ Some "table decision" has been offered by the other
        player(s) in the game, e.g. to abandon the game or whatever.
        Consider this. """

        assert(self.is_table_thread())

        decision_type = args.get('decision_type', None)
        if decision_type is None or decision_type == 'none':
            # There isn't actually a decision pending.
            return

        decision_taken = args.get('decision_taken', None)

        players = args.get('players', None) or {}
        my_decision = players.get(str(self.bga.user_id), None) or ''

        print("consider_table_decision: %s, decision taken: %s, my_decision: %s" % (decision_type, decision_taken, my_decision))
        #print(args)

        if decision_taken or (my_decision and my_decision != 'undecided'):
            # We've previously cast our decision on this question.
            return

        decision = None
        if decision_type == 'abandon':
            # Someone wants to abandon the game, we'll charitably go
            # along with that.
            decision = 1
        elif decision_type == 'switch_tb':
            # Someone wants to switch to turn-based mode, what is
            # that?  Email?  We don't support that.
            decision = 0
        else:
            print("Unhandled table decision_type %s" %(decision_type))

        if decision is not None:
            # All right, register our decision.
            decide_url = 'https://boardgamearena.com/table/table/decide.html'
            decide_params = {
                'decision' : decision,
                'table' : self.table_id,
                }

            r = self.bga.session.get(decide_url, params = decide_params)
            assert(r.status_code == 200)
            dict = json.loads(r.text)
            if not int(dict['status']):
                print("Unexpected result from %s" % (r.url))
                print(dict)

            if decision_type == 'abandon':
                self.game_inactive = True

    def table_notification(self, notification_type, data_dict, live):
        """ A new asynchronous notification has arrived, or possibly
        we are fetching stale notifications at startup.  This method
        is called only in the table thread. """

        assert(self.is_table_thread())

        self.last_message = time.time()
        args = data_dict.get('args', {})
        if notification_type == 'tableInfosChanged':
            print("tableInfosChanged")
            self.__apply_table_infos(args)
        elif notification_type == 'allPlayersAccepted':
            print("allPlayersAccepted")
        elif notification_type == 'tableDecision':
            self.consider_table_decision(args)
        elif notification_type in ['simpleNote', 'simpleNode']:
            note = data_dict.get('log')
            print("simpleNote: %s" % (note))
        elif notification_type == 'yourturnack':
            print("yourturnack")
        elif notification_type == 'wakeupPlayers':
            print("wakeupPlayers")
        elif notification_type == 'gameStateChange':
            print("gameStateChange, id is %s, activePlayer is %s, live is %s" % (self.game_state.get('id', None), self.game_state.get('active_player', None), live))
            self.update_game_state(args, live)
        elif notification_type == 'updateReflexionTime':
            print("updateReflexionTime")
        elif notification_type == 'finalScore':
            print("finalScore")
        elif notification_type == 'gameResultNeutralized':
            print("gameResultNeutralized")
        elif notification_type == 'playerstatus':
            print("playerstatus")
        elif notification_type == 'resultsAvailable':
            print("resultsAvailable")
        elif notification_type == 'wouldlikethink':
            print("wouldlikethink")
        else:
            print("Unhandled table notification type %s: %s" % (notification_type, data_dict))

    def update_game_state(self, game_state, live):
        assert(self.is_table_thread())

        self.game_state = game_state
        if live:
            self.consider_turn()

    def abandon_game(self):
        """ When a derived class determines the game has dropped into
        an invalid state, it should call this method.  This will
        propose a group abandon, which should shut down the game if we
        were the only player left.  This may be called in either the
        main thread or the table thread. """

        with self.lock:
            status = self.table_infos['status']
            if status == 'open' or not self.accepted_start:
                # If the game is still open, we have to quit it rather
                # than abandon it.
                quit_url = 'https://boardgamearena.com/table/table/quitgame.html'
                quit_params = {
                    's' : 'table_quitgame',
                    'table' : self.table_id,
                    }
                #?table=229290475&neutralized=true&s=table_quitgame

            else:
                # If the game has already started, we have to abandon it.
                quit_url = 'https://boardgamearena.com/table/table/decide.html'
                quit_params = {
                    'src' : 'menu',
                    'type' : 'abandon',
                    'decision' : 1,
                    'table' : self.table_id,
                    }

            r = self.bga.session.get(quit_url, params = quit_params)
            assert(r.status_code == 200)
            print(r.url)
            dict = json.loads(r.text)
            if int(dict['status']):
                # Successfully abandoned.
                self.game_inactive = True
            print(dict)

    def consider_turn(self):
        """ Called whenever the game changes state, this should look
        around and see if a turn needs to be played. """

        assert(self.is_table_thread())

        if int(self.game_state.get('active_player', 0)) == int(self.bga.user_id):
            self.my_turn()

    def my_turn(self):
        assert(self.is_table_thread())
        pass

    def poll(self):
        """ Called in the table thread from time to time (e.g. once
        per second) to check if anything needs to be done lately. """

        assert(self.is_table_thread())

        if self.accepted_start and self.gameserver == '0':
            # We've accepted the start but we haven't been told a
            # gameserver yet.  Keep checking for the gameserver, it
            # should be coming in soon.
            self.fetch_table_infos()

        if self.game_inactive:
            # After our table has gone inactive (e.g. finished) for a
            # certain amount of time, remove it from the parent's list
            # of tables.
            elapsed = time.time() - self.last_message
            if elapsed > self.inactive_table_timeout:
                self.bga.close_table(self.table_id)
