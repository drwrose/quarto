import requests                 # python -m pip install requests
from bs4 import BeautifulSoup   # python -m pip install beautifulsoup4
import os
import time
import logging
import threading
import re
import json
import queue
from BGANotifications import BGANotifications
from BGAQuarto import BGAQuarto

from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1

class BoardGameArena:
    """ This class maintains a session to BoardGameArena, via the
    Requests Python library. """

    # Don't try to play more than this number of games at once.
    max_simultaneous_games = 2

    def __init__(self):

        # Record the current thread, or "main thread" of this application.
        self.main_thread = threading.current_thread()

        # This is the parent of the top-level notification channels,
        # which listen for game invites and such.  Each BGATable also
        # has its own set of notification channels.
        self.notifications = BGANotifications(self, name = 'top', auto_restart = True)

        # The dictionary of all BGATable objects, indexed by table_id.
        self.tables = {}

        # A temporary holding place for closed tables.
        self.closed_tables = queue.Queue()

        # Create the web session, which stores all of the login
        # cookies and whatnot.
        self.session = requests.Session()

        self.login()

        notification = self.notifications.create_notification_session(message_callback = self.__message_callback)

        # Now we can subscribe to the basic channels.
        notification.subscribe_channels(
            # This channel contains game requests and generally
            # handles the game-startup sequence.
            "/player/p%s" % (self.user_id),

            # These other channels are subscribed to by the actual BGA
            # client, but I don't think any of them are relevant to
            # us.  They're presumably messages like "The server is
            # going down now!" or "Table xxxx is looking for
            # players!".
            ## "/general/emergency",
            ## "/chat/general",
            ## "/tablemanager/global",
            ## "/tablemanager/detailled",
            ## "/tablemanager/globalasync",
            )

        self.fetch_table_history()

    def cleanup(self):
        """ Stops any threads and closes any sockets, in preparation
        for shutdown. """

        self.notifications.cleanup()

        # Since a table might remove itself from this list at any
        # time, we go through some effort to be thread-safe here.
        table_ids = list(self.tables.keys())
        while table_ids:
            for table_id in table_ids:
                self.close_table(table_id)

            # Probably there won't have been any new tables added to
            # the list while we did that, since these are only added
            # in the main thread I think; but what the heck, we
            # double-check.
            table_ids = list(self.tables.keys())

        # Now all tables have been moved to the closed_tables queue,
        # clean them up properly.
        self.cleanup_closed_tables()

    def cleanup_closed_tables(self):
        """ Called in the main thread to finally cleanup tables that
        were recently moved to self.closed_tables(). """

        try:
            while True:
                table = self.closed_tables.get(block = False)
                table.cleanup()
        except queue.Empty:
            pass

    def login(self):
        """ Log in to Board Game Arena. """

        # Read the login credentials from bga_credentials.txt
        thisdir = os.path.dirname(__file__)
        credentials_filename = os.path.join(thisdir, 'bga_credentials.txt')
        if not os.path.exists(credentials_filename):
            message = 'Could not find %s' % (credentials_filename)
            raise RuntimeError(message)

        credentials = open(credentials_filename, 'r').readlines()
        if len(credentials) < 2:
            message = 'Credentials not found in %s' % (credentials_filename)
            raise RuntimeError(message)

        bga_username = credentials[0].strip()
        bga_password = credentials[1].strip()

        # We start by getting the login form, which we need to extract
        # the csrf_token.
        form_url = 'https://en.boardgamearena.com/account'
        r = self.session.get(form_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        csrf_token = soup.find(id='csrf_token')['value']

        # Now we can post the username/password and log in.
        login_url = 'https://en.boardgamearena.com/account/account/login.html'
        login_data = {
            'email' : bga_username,
            'password' : bga_password,
            #'rememberme' : 'on',
            'csrf_token' : csrf_token,
            }
        r = self.session.post(login_url, data = login_data)
        json = r.json()
        if not int(json['status']) or not json['data']['success']:
            message = 'Unable to log into Board Game Arena: %s' % (json.get('error'))
            raise RuntimeError(message)

        infos = json['data']['infos']
        self.user_name = infos['name']
        self.user_id = infos['id']
        self.socketio_credentials = infos['socketio_cred']

        # Now we are successfully logged in, with appropriate login
        # cookies stored in self.session.
        print("Successfully logged in as %s" % (self.user_name))

    def fetch_table_history(self):
        """ Tries to get the set of tables that we are already
        involved with.  This is especially useful at startup, when we
        may have missed some past notifications. """

        # We just query the front page and look for globalUserInfos in
        # the response.
        history_url = 'https://boardgamearena.com/'
        r = self.session.get(history_url)

        m = re.search('[ \t]+globalUserInfos=(.*);', r.text)
        if m is None:
            print("globalUserInfos not found")
            return

        json_text = m.group(1)
        user_infos = json.loads(json_text)
        table_ids = user_infos['table_infos']['tables']
        if not table_ids:
            print("No existing tables.")
        else:
            for table_id, args in table_ids.items():
                table_id = int(table_id)
                game_name = args.get('game_name', None)
                print("Found table %s, %s" % (table_id, game_name))
                self.add_table(table_id, game_name = game_name)

    def serve(self):
        """ Does not return until explicitly stopped. """

        print("Serving.")
        try:
            while True:
                # Check for recent messages.
                self.notifications.dispatch(block = True, timeout = 1)
                self.cleanup_closed_tables()

        except KeyboardInterrupt:
            print("KeyboardInterrupt, exiting.")
            return

        finally:
            self.cleanup()

    def __message_callback(self, channel, bgamsg_data, live):
        """ A notification is received on the named channel, one of
        the ones we subscribed to in the constructor. """

        #print("Basic notification on %s: %s" % (channel, data))
        data = bgamsg_data['data']
        if channel == '/player/p%s' % (self.user_id):
            data_dict = data[0]
            notification_type = data_dict['type']
            args = data_dict.get('args', {})
            if notification_type == 'updatePlayerTableStatus':
                self.update_player_table_status(args)

            elif notification_type == 'playerstatus':
                print("player_status %s is %s" % (args['player_name'], args['player_status']))

            elif notification_type == 'groupUpdate':
                group_id = args['group']
                print("groupUpdate for %s" % (group_id))

            elif notification_type == 'matchmakingGameStart':
                table_id = int(args['table_id'])
                print("matchmakingGameStart for %s" % (table_id))

            elif notification_type == 'shouldAcceptGameStart':
                table_id = int(args['table_id'])
                print("shouldAcceptGameStart for %s" % (table_id))
                table = self.add_table(table_id)
                if table:
                    table.accept_start()

            elif notification_type == 'proposeRematch':
                table_id = int(args['table_id'])
                print("proposeRematch for %s" % (table_id))

            elif notification_type == 'updatePlayerNotifCount':
                print("updatePlayerNotifCount")

            else:
                print("Unhandled player notification type %s: %s" % (notification_type, data_dict))
        else:
            print("Unhandled notification on %s: %s" % (channel, data))

    def update_player_table_status(self, args):
        status = args['status']
        game_name = args.get('game_name', None)
        table_id = int(args.get('table_id', 0))
        print("update_player_table_status: %s, %s at table %s" % (status, game_name, table_id))

        self.add_table(table_id, game_name = game_name)

    def num_active_tables(self):
        """ Returns the number of tables we're currently involved in
        (or about to be involved in). """

        count = 0
        for table in self.tables.values():
            if not table.game_inactive:
                count += 1
        return count

    def add_table(self, table_id, game_name = None):
        """ Adds the table to self.tables if it wasn't already there;
        in any case, fetches the latest table_infos for the table.
        Returns the table, or None if the table isn't valid. """

        if table_id in self.tables:
            # Already there.
            return self.tables[table_id]

        if game_name is None:
            # Ignore this, we don't need to create a game we don't know.
            return None

        if self.num_active_tables() > self.max_simultaneous_games:
            # Too busy, maybe later.
            print("Already involved in %s games" % (self.num_active_tables()))
            self.refuse_invitation(table_id)
            return None

        # Create a new table entry.
        table = None
        if game_name == 'quarto':
            table = BGAQuarto(self, table_id)

        if not table:
            print("Don't know how to play %s" % (game_name))
            self.refuse_invitation(table_id)
            return None

        self.tables[table_id] = table
        return table

    def refuse_invitation(self, table_id):
        """ Tells the player no thank you, when we're invited to a
        game we can't play. """

        refuse_url = 'https://boardgamearena.com/table/table/refuseInvitation.html'
        refuse_params = {
            'table' : table_id,
            }

        r = self.session.get(refuse_url, params = refuse_params)
        print(r.url)
        assert(r.status_code == 200)
        print(r.text)

    def close_table(self, table_id):
        # Moves the table to the closed_table list for future cleanup.
        # This may be called in the table's own table_thread, or in
        # the main thread at cleanup time.

        print("close_table(%s)" % (table_id))
        table = self.tables.get(table_id, None)
        if table:
            assert(table.table_id == table_id)
            del self.tables[table_id]
            self.closed_tables.put(table)
