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

    def __init__(self, bga, table_id):
        print("Creating table %s for %s" % (self, table_id))
        self.bga = bga
        self.table_id = table_id
        self.table_infos = None

        self.notification = self.bga.create_notification_session(self.__table_notification)
        self.notification.subscribe_channels(
            "/table/t%s" % (self.table_id),
            )

        self.update_table_info()

    def cleanup(self):
        self.bga.close_notification_session(self.notification)
        self.notification = None

    def update_table_info(self):
        tableinfo_url = 'https://boardgamearena.com/table/table/tableinfos.html'
        tableinfo_params = {
            'id' : self.table_id,
            }

        r = self.bga.session.get(tableinfo_url, params = tableinfo_params)
        self.table_info = json.loads(r.text)
        status = self.table_info['data']['status']
        print("updated table_info for %s, status = %s" % (self.table_id, status))
        if status == 'open':
            self.accept_invite()
        elif status == 'setup':
            self.accept_start()
        elif status == 'finished':
            print("Game is finished.")
            self.bga.close_table(self)
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

        r = self.bga.session.get(accept_url, params = accept_params)
        assert(r.status_code == 200)
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
                self.update_table_info(data_dict['args'])
            elif notification_type == 'allPlayersAccepted':
                print("allPlayersAccepted")
            elif notification_type == 'tableDecision':
                decision_type = data_dict['decision_type']
                print("tableDecision: %s" % (decision_type))
            else:
                print("Unhandled table notification type %s: %s" % (notification_type, data_dict))
        else:
            print("Unhandled table notification on %s: %s" % (channel, data))

    def update_table_info(self, args):
        self.table_info = args
