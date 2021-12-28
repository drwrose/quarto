import re
import json
import requests          # python -m pip install requests
import websocket         # python -m pip install websocket-client
import threading
import time
import ssl

class BGANotificationSession:
    eio = '3'  # Don't know what this is really?

    # Messages
    client_greeting = '2probe'  # Not really sure what this means

    server_greeting = '3probe' # Not really sure what this means
    client_server_response = '5' # Not really sure what this means

    client_heartbeat = '2'
    server_heartbeat = '3'

    def __init__(self, bga):
        self.bga = bga

        # https://r2.boardgamearena.net/r/?user=86152093&name=drwrose&credentials=4faffebfc39f554ccade3ae252bdc388&EIO=3&transport=polling&t=NtuCSTy&sid=W5CFZFPJAYxZJCXcASub
        # -> JSON notification update, or "ok"

        # https://r1.boardgamearena.net/3/r/?user=86152093&name=drwrose&credentials=4faffebfc39f554ccade3ae252bdc388&EIO=3&transport=polling&t=NtuCSWp&sid=o-dqzPJc-nnLPN1mAF-3
        # POST: 31:42["join","/table/ts226845327"]30:42["join","/player/p86152093"]

        # websocket connection?
        #https://r2.boardgamearena.net/r/?user=86152093&name=drwrose&credentials=4faffebfc39f554ccade3ae252bdc388&EIO=3&transport=polling&t=Ntu9pqW
        # -> 96:0{"sid":"tKSrqutPoxgZKJeMAF2z","upgrades":["websocket"],"pingInterval":25000,"pingTimeout":5000}2:40

        #wss://r1.boardgamearena.net/3/r/?user=86152093&name=drwrose&credentials=4faffebfc39f554ccade3ae252bdc388&EIO=3&transport=websocket&sid=tKSrqutPoxgZKJeMAF2z

        subscribe_url = 'https://r2.boardgamearena.net/r/'
        subscribe_params = {
            'user' : self.bga.user_id,
            'name' : self.bga.user_name,
            'credentials' : self.bga.socketio_credentials,
            'EIO' : self.eio,
            'transport' : 'polling',
            #'t' : 'Ntu9pqW',
            }

        r = self.bga.session.get(subscribe_url, params = subscribe_params)
        messages = dict(self.parse_messages(r.text))

        comm_protocol = messages[0]
        self.sid = comm_protocol['sid']
        self.ping_interval = int(comm_protocol['pingInterval']) # time in ms
        self.ping_timeout = int(comm_protocol['pingTimeout']) #?
        self.ws_thread = None
        self.heartbeat_thread = None

        # Now start a websocket connection.  As a hack around the fact
        # that the requests module refuses to format parameters for
        # non-http URLs, we pass the URL as https originally, then
        # change it to wss below.
        websocket_url = 'https://r2.boardgamearena.net/r/'
        websocket_params = {
            'user' : self.bga.user_id,
            'name' : self.bga.user_name,
            'credentials' : self.bga.socketio_credentials,
            'EIO' : self.eio,
            'transport' : 'websocket',
            'sid' : self.sid,
            }

        parser = requests.PreparedRequest()
        parser.prepare_url(url = websocket_url, params = websocket_params)

        # Change the url from https:// to wss://.
        url = 'wss' + parser.url[5:]
        #print(url)

        #websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(url,
                                         on_open = self.__ws_open,
                                         on_message = self.__ws_message,
                                         on_error = self.__ws_error,
                                         on_close = self.__ws_close)

        self.start_ws()

        #return

        # Now that we've connected to the websocket for notifications,
        # sign up to certain message channels.
        subscribe_url = 'https://r2.boardgamearena.net/r/'
        subscribe_params = {
            'user' : self.bga.user_id,
            'name' : self.bga.user_name,
            'credentials' : self.bga.socketio_credentials,
            'EIO' : self.eio,
            'transport' : 'polling',
            'sid' : self.sid,
            }

        subscribe_messages = [
            (42, ["join","/general/emergency"]),
            ## (42, ["join","/chat/general"]),
            ## (42, ["join","/player/p86238453"]),
            ## (42, ["join","/group/g3781377"]),
            ## (42, ["join","/tablemanager/global"]),
            ## (42, ["join","/tablemanager/detailled"]),
            ## (42, ["join","/tablemanager/globalasync"]),
            ## (42, ["join",["/group/g6563374"]]),
            ## (42, ["join","/table/t227216683"]),
            ]
        subscribe_text = self.format_messages(subscribe_messages)
        print(subscribe_text)

        r = self.bga.session.post(subscribe_url, params = subscribe_params, data = subscribe_text)
        print(r.url)
        print(r)
        print(r.text)
        import pdb; pdb.set_trace()

    def format_messages(self, messages):
        """ Given a list of (id, object) tuples, formats them into a
        single string to send as a message. """

        text = self.__format_messages(messages)
        messages2 = self.__parse_messages(text)
        if (messages != messages2):
            print(messages)
            print(messages2)
            import pdb; pdb.set_trace()
        return text

    def __format_messages(self, messages):
        """ Given a list of (id, object) tuples, formats them into a
        single string to send as a message. """

        text = ''
        for id, object in messages:
            if object is None:
                json_text = ''
            else:
                json_text = json.dumps(object, separators = (',', ':'))

            # The length includes the length of the id number.
            this_text = '%s%s' % (id, json_text)
            length = len(this_text)

            text += '%s:%s' % (length, this_text)

        return text

    def parse_messages(self, text):
        """ Returns a list of (id, json) tuples, extracted from the
        notification response. """

        messages = self.__parse_messages(text)
        text2 = self.__format_messages(messages)
        if (text != text2):
            print(text)
            print(text2)
            import pdb; pdb.set_trace()

        return messages

    def __parse_messages(self, text):
        """ Returns a list of (id, json) tuples, extracted from the
        notification response. """

        # We expect a set of messages in the form of repeated strings
        # of 99:99[json], where the first 99 is the character length
        # of 99[json], and the second 99 is the id.

        messages = []

        pattern = re.compile('([0-9]+):([0-9]+)')
        p = 0
        while p < len(text):
            # Pull out the next message.
            m = pattern.match(text, p)
            if m is None:
                message = 'Unexpected response from BGA at position %s: %s' % (p, text)
                raise RuntimeError(message)

            length, id = m.groups()
            length = int(length)
            id = int(id)

            # The next character after the id is the beginning of the
            # message data.
            data_start = m.end(0)

            # The end of the message data is measured from the start
            # of id.
            data_end = m.start(2) + length
            assert(data_end <= len(text))

            json_text = text[data_start : data_end].strip()
            if json_text:
                try:
                    json_data = json.loads(json_text)
                except json.decoder.JSONDecodeError:
                    print("Invalid JSON text: %s" % (json_text))
                    import pdb; pdb.set_trace()
            else:
                json_data = None
            messages.append((id, json_data))
            p = data_end

        return messages

    def poll(self):
        """ Should be called from time to time to do some stuff. """

        ## print("Polling.")
        ## poll_url = 'https://r2.boardgamearena.net/r/'
        ## poll_params = {
        ##     'user' : self.bga.user_id,
        ##     'name' : self.bga.user_name,
        ##     'credentials' : self.bga.socketio_credentials,
        ##     'EIO' : self.eio,
        ##     'transport' : 'polling',
        ##     'sid' : self.sid,
        ##     #'t' : 'Ntu9pqW',
        ##     }

        ## print(poll_params)
        ## r = self.bga.session.get(poll_url, params = poll_params)
        ## messages = self.parse_messages(r.text)

        #print(messages)
        pass

    def __ws_message(self, ws, message):
        print("__ws_message(%s): %s" % (ws, message))
        if message == self.server_greeting:
            ws.send(self.client_server_response)
            if not self.heartbeat_thread:
                self.start_heartbeat()

    def __ws_error(self, ws, error):
        print("__ws_error(%s): %s" % (ws, error))

    def __ws_close(self, ws, close_status_code, close_msg):
        print("__ws_close(%s)" % (ws))

        self.stop_heartbeat()

    def __ws_open(self, ws):
        print("__ws_open(%s) vs. %s" % (ws, self.ws))

        ws.send(self.client_greeting)

    def start_ws(self):
        assert not self.ws_thread
        self.ws_thread = threading.Thread(target = self.__ws_thread_main)
        self.ws_thread.start()

    def __ws_thread_main(self):
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def start_heartbeat(self):
        if self.heartbeat_thread:
            self.stop_heartbeat()

        self.heartbeat_thread = threading.Thread(target = self.__heartbeat_thread_main)
        self.heartbeat_thread.start()

    def stop_heartbeat(self):
        if self.heartbeat_thread:
            thread = self.heartbeat_thread
            self.heartbeat_thread = None
            thread.join()

    def __heartbeat_thread_main(self):
        while self.heartbeat_thread:
            self.ws.send(self.client_heartbeat)
            time.sleep(self.ping_interval / 1000.0)
