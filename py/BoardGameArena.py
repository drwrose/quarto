import requests                 # python -m pip install requests
from bs4 import BeautifulSoup   # python -m pip install beautifulsoup4
import os
import time
import logging
import threading
from BGANotificationSession import BGANotificationSession

from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1

class BoardGameArena:
    """ This class maintains a session to BoardGameArena, via the
    Requests Python library. """

    def __init__(self):

        self.notifications = []
        self.notification_cvar = threading.Condition()

        # Create the web session, which stores all of the login
        # cookies and whatnot.
        self.session = requests.Session()

        self.login()

        notification = self.create_notification_session(self.__basic_notification)

        # Now we can subscribe to the basic channels.
        notification.subscribe_channels(
            ## "/general/emergency",  # Probably we don't need this.
            ## "/chat/general",  # or this
            "/player/p%s" % (self.user_id),
            "/tablemanager/global",
            "/tablemanager/detailled",
            "/tablemanager/globalasync",
            ## "/table/t227216683",
            )

        #https://boardgamearena.com/table/table/tableinfos.html?id=226845327&dojo.preventCache=1640545851803
        # -> JSON data about table and game, doesn't change with turns

        # https://boardgamearena.com/1/quarto/quarto/notificationHistory.html?table=226845327&from=6&privateinc=1&history=1&dojo.preventCache=1640546551506
        # -> JSON data about past moves, changes with turns

        # https://boardgamearena.com/1/quarto/quarto/wakeup.html?myturnack=true&table=226845327&dojo.preventCache=1640546551483
        # -> JSON status indication, basic heartbeat?

        # Pushing moves
        #https://boardgamearena.com/4/quarto/quarto/selectPiece.html?number=1&table=226600309&dojo.preventCache=1640462571803
        #https://boardgamearena.com/4/quarto/quarto/placePiece.html?x=1&y=4&table=226600309&dojo.preventCache=1640462661462

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

    def create_notification_session(self, message_callback):
        """ Signs up for notifications of events from BGA. """
        notification = BGANotificationSession(self, message_callback)
        self.notifications.append(notification)
        return notification

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

    def __basic_notification(self, channel, data):
        """ A notification is received on the named channel, one of
        the ones we subscribed to in the constructor. """

        print("Basic notification on %s: %s" % (channel, data))
