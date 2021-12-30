import re
import json
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

        self.notification = self.bga.create_notification_session(self.__table_notification)
        self.notification.subscribe_channels(
            "/table/t%s" % (self.table_id),
            )

        self.fetch_table_infos()

    def cleanup(self):
        self.bga.close_notification_session(self.notification)
        self.notification = None

    def fetch_table_infos(self):
        tableinfo_url = 'https://boardgamearena.com/table/table/tableinfos.html'
        tableinfo_params = {
            'id' : self.table_id,
            }

        r = self.bga.session.get(tableinfo_url, params = tableinfo_params)
        dict = json.loads(r.text)
        table_infos = dict['data']
        self.__update_table_infos(table_infos)

    def fetch_notification_history(self):
        # TODO: where does this URL come from?
        history_url = 'https://boardgamearena.com/6/quarto/quarto/notificationHistory.html'
        history_params = {
            'table' : self.table_id,
            'from' : 2,
            'privateinc' : 1,
            'history' : 1,
            }

        r = self.bga.session.get(history_url, params = history_params)
        dict = json.loads(r.text)

        print("Found %s past notifications" % (len(dict['data']['data'])))

    def __update_table_infos(self, table_infos):
        """ A new table_infos dictionary has been acquired.  Store it,
        and deal with whatever it says. """

        self.table_infos = table_infos
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
            self.fetch_notification_history()
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

    def __table_notification(self, channel, data):
        """ A notification is received on the named channel, one of
        the ones we subscribed to in the constructor. """

        #print("Table notification on %s: %s" % (channel, data))
        if channel == '/table/t%s' % (self.table_id):
            data_dict = data[0]
            notification_type = data_dict['type']
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
            else:
                print("Unhandled table notification type %s: %s" % (notification_type, data_dict))
        else:
            print("Unhandled table notification on %s: %s" % (channel, data))
