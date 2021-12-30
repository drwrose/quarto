import re
import json
import ast
import requests          # python -m pip install requests
import websocket         # python -m pip install websocket-client
import threading
import time
import ssl
import traceback
import queue

class BGATable:
    """ Manages the connection to a specific "table" or game at
    BGA. """

    #https://boardgamearena.com/6/quarto?table=227990980

    #30:42["join","/table/t227776934"]
    #https://boardgamearena.com/5/quarto/quarto/selectPiece.html?number=1&table=227776934&dojo.preventCache=1640820986745

    # Pushing moves
    #https://boardgamearena.com/4/quarto/quarto/selectPiece.html?number=1&table=226600309&dojo.preventCache=1640462571803
    #https://boardgamearena.com/4/quarto/quarto/placePiece.html?x=1&y=4&table=226600309&dojo.preventCache=1640462661462

    def __init__(self, bga, table_id):
        print("Creating table %s for %s" % (self, table_id))
        self.bga = bga
        self.table_id = table_id
        self.table_infos = None
        self.last_packet_id = 0
        self.game_state = {}

        self.gs_socketio_url = None
        self.gs_socketio_path = None

        self.fetch_table_infos()
        self.fetch_gs_socketio()

        self.notification = self.bga.create_notification_session(
            message_callback = self.__channel_notification,
            socketio_url = self.gs_socketio_url,
            socketio_path = self.gs_socketio_path)

        self.notification.subscribe_channels(
            "/table/t%s" % (self.table_id),
            #"/table/ts%s" % (self.table_id),
            )

        self.fetch_notification_history()

    def cleanup(self):
        self.bga.close_notification_session(self.notification)
        self.notification = None

    def fetch_table_infos(self):
        """ Updates self.table_infos with the most recent data about
        this game from BGA.  This is the top-level information about
        the game and how it is hosted. """

        tableinfo_url = 'https://boardgamearena.com/table/table/tableinfos.html'
        tableinfo_params = {
            'id' : self.table_id,
            }

        r = self.bga.session.get(tableinfo_url, params = tableinfo_params)
        dict = json.loads(r.text)
        table_infos = dict['data']
        self.__update_table_infos(table_infos)

    def fetch_gs_socketio(self):
        """ Updates the gs_socketio_* values, which describe how to
        communicate with the game server directly. """

        table_url = 'https://boardgamearena.com/%s/%s' % (self.gameserver, self.game_name)
        table_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(table_url, params = table_params)

        # Now look for gameui.gs_socketio_url and
        # gameui.gs_socketio_path in that returned page.
        m = re.search('[ \t]+gameui[.]gs_socketio_url=(.*);', r.text)
        if m is None:
            print("gs_socketio_url not found")
        else:
            self.gs_socketio_url = ast.literal_eval(m.group(1))

        m = re.search('[ \t]+gameui[.]gs_socketio_path=(.*);', r.text)
        if m is None:
            print("gs_socketio_path not found")
        else:
            self.gs_socketio_path = ast.literal_eval(m.group(1))

    def fetch_notification_history(self):
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
            self.__channel_notification(channel, bgamsg_data)

    def __update_table_infos(self, table_infos):
        """ A new table_infos dictionary has been acquired.  Store it,
        and deal with whatever it says. """

        self.table_infos = table_infos
        self.gameserver = self.table_infos['gameserver']
        self.game_name = self.table_infos['game_name']

        status = self.table_infos['status']
        print("updated table_info for %s, status = %s" % (self.table_id, status))
        if status == 'open':
            me_info = self.table_infos['players'].get(str(self.bga.user_id), None)
            table_status = me_info and me_info['table_status']
            print("table_status = %s" % (table_status))
            if table_status == 'setup':
                # We're not in the game yet, join it.
                self.accept_invite()
            elif table_status == 'expected':
                print("expected")
                self.accept_invite()
            elif table_status == 'play':
                print("playing")
            else:
                print("Unhandled table status %s" % (table_status))
        elif status == 'setup':
            self.accept_start()
        elif status == 'finished':
            print("Game is finished.")
            self.bga.close_table(self)
        elif status == 'play':
            print("Game is actively playing.")
        else:
            print("Unhandled game status %s" % (status))

    def accept_invite(self):
        print("accept_invite")

        accept_url = 'https://boardgamearena.com/table'
        accept_params = {
            'table' : self.table_id,
            'acceptinvit' : '',
            'refreshtemplate' : 1,
            }

        ## r = self.bga.session.get(accept_url, params = accept_params)
        ## assert(r.status_code == 200)
        #print(r.text)

        join_url = 'https://boardgamearena.com/table/table/joingame.html'
        join_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(join_url, params = join_params)
        assert(r.status_code == 200)
        print(r.text)

        print("done accept_invite")

    def accept_start(self):
        accept_url = 'https://boardgamearena.com/table/table/acceptGameStart.html'
        accept_params = {
            'table' : self.table_id,
            }

        r = self.bga.session.get(accept_url, params = accept_params)
        assert(r.status_code == 200)
        print(r.text)

    def send_myturnack(self):
        """ Sends an explicit message to acknowledge that we have seen
        that it's our turn. """

        wakeup_url = 'https://boardgamearena.com/%s/%s/%s/wakeup.html' % (self.gameserver, self.game_name, self.game_name)
        wakeup_params = {
            'myturnack' : 'true',
            'table' : self.table_id,
            }
        r = self.bga.session.get(wakeup_url, params = wakeup_params)
        assert(r.status_code == 200)
        print(r.text)

    def __channel_notification(self, channel, bgamsg_data):
        """ A notification is received on the named channel, one of
        the ones we subscribed to in the constructor. """

        data = bgamsg_data['data']
        packet_id = int(bgamsg_data.get('packet_id', 0))
        #print("Table notification on %s, packet_id %s" % (channel, packet_id))

        if channel == '/table/t%s' % (self.table_id):
            if packet_id > self.last_packet_id:
                self.last_packet_id = packet_id
                for data_dict in data:
                    notification_type = data_dict['type']
                    self.table_notification(notification_type, data_dict)
        elif channel == '/table/ts%s' % (self.table_id):
            data_dict = data[0]
            notification_type = data_dict['type']
            if notification_type == 'updateSpectatorList':
                print("updateSpectatorList")
            else:
                print("Unhandled table s notification type %s: %s" % (notification_type, data_dict))

        else:
            print("Unhandled table notification on %s: %s" % (channel, data))

    def table_notification(self, notification_type, data_dict):
        if notification_type == 'tableInfosChanged':
            print("tableInfosChanged")
            table_infos = data_dict['args']
            self.__update_table_infos(table_infos)
        elif notification_type == 'allPlayersAccepted':
            print("allPlayersAccepted")
        elif notification_type == 'tableDecision':
            decision_type = data_dict.get('decision_type', None)
            print("tableDecision: %s" % (decision_type))
            print(data_dict)
        elif notification_type == 'simpleNote':
            note = data_dict.get('log')
            print("simpleNote: %s" % (note))
        elif notification_type == 'yourturnack':
            print("yourturnack")
        elif notification_type == 'wakeupPlayers':
            print("wakeupPlayers")
        elif notification_type == 'gameStateChange':
            print("gameStateChange")
            self.update_game_state(data_dict['args'])
        elif notification_type == 'updateReflexionTime':
            print("gameStateChange")
            self.reflexion_time = data_dict['args']
        else:
            print("Unhandled table notification type %s: %s" % (notification_type, data_dict))

    def update_game_state(self, game_state):
        self.game_state = game_state
