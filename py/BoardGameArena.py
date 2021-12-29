import requests                 # python -m pip install requests
from bs4 import BeautifulSoup   # python -m pip install beautifulsoup4
import os
import time
import logging
import threading
from BGANotificationSession import BGANotificationSession
from BGATable import BGATable

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

        # Notification for new game invitation
        # 42["bgamsg","{\"packet_type\":\"single\",\"channel\":\"\\/player\\/p86238453\",\"id\":0,\"data\":[{\"time\":\"18:19\",\"uid\":\"61cbc5a3204b4\",\"type\":\"updatePlayerTableStatus\",\"log\":\"\",\"args\":{\"table_id\":\"227508494\",\"game_name\":\"quarto\",\"async\":0,\"matchmaking\":0,\"status\":\"expected\",\"change\":0}}],\"time\":1640744355}"]

        # Notification for new game invitation on table channel
        # {"packet_type":"single","channel":"\/table\/t227508494","id":1,"data":[{"time":"18:19","uid":"61cbc5a321d71","type":"tableInfosChanged","log":"${change_log}","args":{"id":"227508494","game_id":"39","status":"open","table_creator":"86152093","has_tournament":"0","max_player":"2","level_filter":{"label":{"log":"","args":[]},"details":{"Beginners":true,"Apprentices":true,"Average players":true,"Good players":true,"Strong players":true,"Experts":true,"Masters":true}},"filter_group":"3679652","filter_lang":null,"reputation_filter":{"label":"","details":{"opinion":0,"leave":0,"clock":0,"karma":0}},"progression":"0","presentation":"","cancelled":"0","unranked":"0","min_player":"2","filter_group_name":"drwrose","filter_group_visibility":"public","filter_group_type":"friend","game_name":"quarto","game_max_players":"2","game_min_players":"2","game_player_number":{"2":1},"game_status":"public","game_premium":"0","game_expansion_premium":"0","sandbox":"0","scheduled":"1640744303","gamestart":null,"gameserver":"0","duration":"4","initial_reflexion_time_advice":"0","additional_reflexion_time_advice":"0","siteversion":"211223-1100","gameversion":"170202-1134","log_archived":"0","news_id":null,"player_number_advice":null,"player_number_not_recommended":"","fast":"27","medium":"43","slow":"69","league_number":"3","players":{"86152093":{"id":"86152093","table_status":"play","fullname":"drwrose","avatar":"8233d76f60","rank":1300,"rank_victory":"3","arena_points":"1.1500","table_order":"1","is_admin":"1","is_premium":"1","is_beginner":"0","is_confirmed":"0","status":"online","device":"desktop","decision":null,"player_country":"US","gender":null,"grade":"3","played":"15","realPlayed":"0","prestige":777,"th_name":null,"thumb_up":"0","thumb_down":"0","recent_games":"12","recent_leave":"0","recent_clock":"0","karma":"100","karma_alert":"no","victory":"3","hit":33,"ip":"47.34.178.232","languages_fluent":null,"languages_normal":"en","ranksummary":0,"country":{"flag":229,"name":"United States","cur":"USD","code":"US","flag_x":352,"flag_y":99},"languages":{"en":{"name":"English","code":"en_US","level":0}},"freeaccount":false,"premiumaccount":true,"rank_no":null,"same_ip":1,"awards":[{"id":"48003104","player":"86152093","game":"39","type_id":"2","date":"1602541551","defending":"1","linked_tournament":null,"prestige":"8","tgroup":null,"tournament_name":null,"championship_name":null,"season":null,"group_avatar":null,"name":"3victory","nametr":"%s victories","namearg":3,"prestigeclass":0},{"id":"47764561","player":"86152093","game":"39","type_id":"1","date":"1602196398","defending":"1","linked_tournament":null,"prestige":"4","tgroup":null,"tournament_name":null,"championship_name":null,"season":null,"group_avatar":null,"name":"firstvictory","nametr":"firstvictory_trophy_name","namearg":1,"prestigeclass":0},{"id":"48002817","player":"86152093","game":"39","type_id":"13","date":"1602541030","defending":"1","linked_tournament":null,"prestige":"3","tgroup":null,"tournament_name":null,"championship_name":null,"season":null,"group_avatar":null,"name":"5played","nametr":"Enthusiast","namearg":5,"prestigeclass":0}]},"86238453":{"id":"86238453","table_status":"play","fullname":"drwrose2","avatar":"x00000","rank":1300,"rank_victory":"0","arena_points":"1.1500","table_order":"2","is_admin":"0","is_premium":"0","is_beginner":"0","is_confirmed":"0","status":"online","device":"desktop","decision":null,"player_country":"US","gender":null,"grade":"3","played":"0","realPlayed":"0","prestige":106,"th_name":null,"thumb_up":"0","thumb_down":"0","recent_games":"0","recent_leave":"0","recent_clock":"0","karma":"75","karma_alert":"no","victory":"0","hit":0,"ip":"47.34.178.232","languages_fluent":null,"languages_normal":"en","ranksummary":0,"country":{"flag":229,"name":"United States","cur":"USD","code":"US","flag_x":352,"flag_y":99},"languages":{"en":{"name":"English","code":"en_US","level":0}},"freeaccount":true,"premiumaccount":false,"rank_no":null,"same_ip":1}},"level_filter_r":"127","reputation_filter_r":"0","current_player_nbr":2,"current_present_player_nbr":2,"player_display":["86152093","86238453"],"options":{"201":{"name":"Game mode","values":[{"name":"Normal mode"},{"name":"Training mode"},{"name":"Arena mode","no_player_selection":true}],"type":"enum","value":"1"},"200":{"name":"Game speed","values":{"0":{"name":"Real-time \u2022 Fast speed","shortname":"Real-time \u2022 Fast"},"1":{"name":"Real-time \u2022 Normal speed","shortname":"Real-time \u2022 Normal"},"2":{"name":"Real-time \u2022 Slow speed","shortname":"Real-time \u2022 Slow"},"5":{"name":"Real-time \u2022 Fixed time limit","no_player_selection":true,"shortname":"Real-time"},"9":{"name":"No time limit &bull; recommended with friends only","no_player_selection":true,"shortname":"No time limit &bull; recommended with friends only"},"10":{"name":"Fast Turn-based &bull; 24 moves per day","shortname":"Fast Turn-based &bull; 24 moves per day"},"11":{"name":"Fast Turn-based &bull; 12 moves per day","shortname":"Fast Turn-based &bull; 12 moves per day"},"12":{"name":"Fast Turn-based &bull; 8 moves per day","shortname":"Fast Turn-based &bull; 8 moves per day"},"13":{"name":"Turn-based &bull; 4 moves per day","shortname":"Turn-based &bull; 4 moves per day"},"14":{"name":"Turn-based &bull; 3 moves per day","shortname":"Turn-based &bull; 3 moves per day"},"15":{"name":"Turn-based &bull; 2 moves per day","shortname":"Turn-based &bull; 2 moves per day"},"17":{"name":"Turn-based &bull; 1 move per day","shortname":"Turn-based &bull; 1 move per day"},"19":{"name":"Turn-based &bull; 1 move per 2 days","shortname":"Turn-based &bull; 1 move per 2 days"},"20":{"name":"No time limit &bull; recommended with friends only","shortname":"No time limit &bull; recommended with friends only"},"21":{"name":"Turn-based &bull; Fixed time limit","no_player_selection":true,"shortname":"Turn-based"}},"type":"enum","value":"9","displaycondition":[{"type":"otheroption","id":201,"value":[0,2]}]},"204":{"name":"Time allotted to each player","values":[],"type":"enum","value":"","displaycondition":[{"type":"otheroption","id":200,"value":[5,21]}],"template":{"namearg":"%s minutes","default":0}},"206":{"name":"Playing hours","values":[{"name":"24 hours a day (no playing hours)","disable":true},{"name":"00:00 &rarr; 12:00"},{"name":"01:00 &rarr; 13:00"},{"name":"02:00 &rarr; 14:00"},{"name":"03:00 &rarr; 15:00"},{"name":"04:00 &rarr; 16:00"},{"name":"04:00 &rarr; 17:00"},{"name":"06:00 &rarr; 18:00"},{"name":"07:00 &rarr; 19:00"},{"name":"08:00 &rarr; 20:00"},{"name":"09:00 &rarr; 21:00"},{"name":"10:00 &rarr; 22:00"},{"name":"11:00 &rarr; 23:00"},{"name":"12:00 &rarr; 00:00"},{"name":"13:00 &rarr; 01:00"},{"name":"14:00 &rarr; 02:00"},{"name":"15:00 &rarr; 03:00"},{"name":"16:00 &rarr; 04:00"},{"name":"17:00 &rarr; 05:00"},{"name":"18:00 &rarr; 06:00"},{"name":"19:00 &rarr; 07:00"},{"name":"20:00 &rarr; 08:00"},{"name":"21:00 &rarr; 09:00"},{"name":"22:00 &rarr; 10:00"},{"name":"23:00 &rarr; 11:00"}],"type":"enum","value":0,"displaycondition":[{"type":"otheroption","id":200,"value":[10,11,12,21]}]},"100":{"name":"Game variant","values":{"1":{"name":"Standard","tmdisplay":"Standard"},"2":{"name":"Advanced (2x2)","tmdisplay":"Advanced (2x2)"}},"type":"enum","value":"1"}},"admin_id":"86152093","options_order":[201,200,204,206,100],"beta_option_selected":false,"alpha_option_selected":false,"not_recommend_player_number":[],"beginner_not_recommended_player_number":[],"rtc_mode":null,"estimated_duration":4,"time_profile":{"additional_time_per_move":2592000,"maximum_time_per_move":691200,"extra_time_to_think_to_expel":518400,"initial_time_to_thing":7776000},"player_name":"drwrose2","tablelog":"${player_name} joins the game","i18n":["game_name_tr"],"game_name_tr":"quarto_displayed","change_log":{"log":"${player_name} joins the game","args":{"player_name":"drwrose2"}},"seemore":"table?table=227508494","reload_reason":"expectedPlayerJoinGame"}}],"time":1640744355}

        # Accept game invitation
        # https://boardgamearena.com/table?table=227508494&acceptinvit=&refreshtemplate=1&dojo.preventCache=1640744354664

        # https://boardgamearena.com/table/table/joingame.html?table=227508494&dojo.preventCache=1640744355133

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

    def __basic_notification(self, channel, data):
        """ A notification is received on the named channel, one of
        the ones we subscribed to in the constructor. """

        #print("Basic notification on %s: %s" % (channel, data))
        if channel == '/player/p%s' % (self.user_id):
            data_dict = data[0]
            notification_type = data_dict['type']
            if notification_type == 'updatePlayerTableStatus':
                self.update_player_table_status(data_dict['args'])
            else:
                print("Unhandled player notification type %s: %s" % (notification_type, data_dict))
        else:
            print("Unhandled notification on %s: %s" % (channel, data))

    def update_player_table_status(self, args):
        status = args['status']
        game_name = args.get('game_name', None)
        table_id = args.get('table_id', None)
        print("update_player_table_status: %s, %s at table %s" % (status, game_name, table_id))

        self.update_table(table_id)

    def update_table(self, table_id):
        if table_id in self.tables:
            # Already there, but maybe there's an update in status.
            self.tables[table_id].update_table_info()
            return

        # Create a new table entry.
        table = BGATable(self, table_id)
        self.tables[table_id] = table

    def close_table(self, table):
        del self.tables[table.table_id]
        table.cleanup()
