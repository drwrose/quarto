import requests                 # python -m pip install requests
from bs4 import BeautifulSoup   # python -m pip install beautifulsoup4
import os
import time
import logging
import threading
import re
import json
from BGANotificationSession import BGANotificationSession
from BGAQuarto import BGAQuarto

from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1

class BoardGameArena:
    """ This class maintains a session to BoardGameArena, via the
    Requests Python library. """

    def __init__(self):

        # The list of all BGANotificationSession objects, and the cvar
        # that is notified when a new notification comes in on one of
        # them.
        self.notifications = []
        self.notification_cvar = threading.Condition()

        # The dictionary of all BGATable objects, indexed by table_id.
        self.tables = {}

        # Create the web session, which stores all of the login
        # cookies and whatnot.
        self.session = requests.Session()

        self.login()

        notification = self.create_notification_session(message_callback = self.__message_callback)

        # Now we can subscribe to the basic channels.
        notification.subscribe_channels(
            ## "/general/emergency",  # Probably we don't need this.
            ## "/chat/general",  # or this
            "/player/p%s" % (self.user_id),
            ## "/tablemanager/global",
            ## "/tablemanager/detailled",
            ## "/tablemanager/globalasync",
            )

        self.fetch_table_history()

        # https://boardgamearena.com/1/quarto/quarto/wakeup.html?myturnack=true&table=226845327&dojo.preventCache=1640546551483
        # -> JSON status indication, basic heartbeat?

    def cleanup(self):
        """ Stops any threads and closes any sockets, in preparation
        for shutdown. """

        self.cleanup_notification_sessions()

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
                game_name = args.get('game_name', None)
                print("Found table %s, %s" % (table_id, game_name))
                self.update_table(table_id, game_name = game_name)

    def create_notification_session(self, message_callback = None, socketio_url = 'https://r2.boardgamearena.net', socketio_path = 'r'):
        """ Signs up for notifications of events from BGA. """
        notification = BGANotificationSession(self, message_callback = message_callback, socketio_url = socketio_url, socketio_path = socketio_path)
        self.notifications.append(notification)
        return notification

    def close_notification_session(self, notification):
        self.notifications.remove(notification)
        notification.cleanup()

    def cleanup_notification_sessions(self):
        """ Stops and removes all previously created notification
        sessions. """

        for notification in self.notifications:
            notification.cleanup()
        self.notifications = []

    def dispatch(self):
        """ Dispatches all pending notifications. """

        for notification in self.notifications:
            notification.dispatch()

    def serve(self):
        """ Does not return, just waits for stuff to happen. """
        print("Serving.")
        try:
            while True:
                with self.notification_cvar:
                    self.notification_cvar.wait(1)
                    self.dispatch()
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
                table_id = args['table_id']
                print("matchmakingGameStart for %s" % (table_id))
            elif notification_type == 'shouldAcceptGameStart':
                table_id = args['table_id']
                print("shouldAcceptGameStart for %s" % (table_id))
                self.update_table(table_id)
            elif notification_type == 'proposeRematch':
                table_id = args['table_id']
                print("proposeRematch for %s" % (table_id))
            else:
                print("Unhandled player notification type %s: %s" % (notification_type, data_dict))
        else:
            print("Unhandled notification on %s: %s" % (channel, data))

    def update_player_table_status(self, args):
        status = args['status']
        game_name = args.get('game_name', None)
        table_id = args.get('table_id', None)
        print("update_player_table_status: %s, %s at table %s" % (status, game_name, table_id))

        self.update_table(table_id, game_name = game_name)

    def update_table(self, table_id, game_name = None):
        if table_id in self.tables:
            # Already there, but maybe there's an update in status.
            self.tables[table_id].fetch_table_infos()
            return

        if game_name is None:
            # Ignore this, we don't need to create a game we don't know.
            return

        # Create a new table entry.
        table = None
        if game_name == 'quarto':
            table = BGAQuarto(self, table_id)

        if not table:
            print("Unable to create table of type %s" % (game_name))
            return

        self.tables[table_id] = table

    def close_table(self, table):
        table_object = self.tables.get(table.table_id, None)
        if table_object is table:
            del self.tables[table.table_id]
        table.cleanup()
