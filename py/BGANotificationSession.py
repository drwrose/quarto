import re
import json
import requests          # python -m pip install requests
import websocket         # python -m pip install websocket-client
import threading
import time
import ssl
import traceback

class BGANotificationSession:
    """ Creates a connection to one of the BGA servers to listen for
    notifications on any number of subscribed channels.  This is BGA's
    mechanism for asynchronous notifications, things like chat
    messages, game invites, and turn notifications.

    You can create multiple BGANotificationSession objects.  Each one
    can connect to a single BGA server, and can subscribe to any
    number of channels on that server, by channel_name.  When a
    notification comes in on any of the named channels, it is added to
    the indicated notification_queue with the specified
    message_callback function, to be eventually called in the main
    thread (by notification_queue.dispatch()).  The callback function
    is made with the parameters message_callback(channel_name,
    message_data, live), where message_data is whatever data is
    associated with the notification, and live is True if the message
    originated "live" from the server; this class always passes True
    for live.  Presumably another class may call the same callback
    method with False for live, so the callback may differentiate.
    Specifically, BGATable does this when loading up past
    notifications at startup.

    Call cleanup() to unsubscribe to all channels in this object, shut
    down the threads, and close the socket.  """

    # Threads should return from join() before this amount of time,
    # otherwise give up.
    thread_join_timeout = 5

    eio = '3'  # Don't know what this is really, but BGA passes it on every URL.

    # Messages
    client_probe_response_msgid = 5 # Not really sure what this means either, but BGA seems to expect it in response to a probe.

    client_ping_msgid = 2
    server_ping_msgid = 3
    msg_probe = 'probe'  # This can be attached to a ping and seems to mean additional data is requested.  We reply with client_probe_response_msgid.

    # The id for most notifications, which is what we really care
    # about here.
    notification_msgid = 42

    # The number of seconds we wait between auto_restarts when a
    # socket is closed or a connection attempt fails.
    restart_wait_seconds = 10

    def __init__(self, bga, parent_name = None, notification_queue = None, message_callback = None, socketio_url = None, socketio_path = None, auto_restart = False):
        # If auto_restart is True, the websocket will reconnect itself
        # if it gets dropped by the server.

        self.bga = bga
        self.notification_queue = notification_queue
        self.message_callback = message_callback
        self.socketio_url = socketio_url
        self.socketio_path = socketio_path
        self.auto_restart = auto_restart
        self.subscribe_url = '%s/%s/' % (self.socketio_url, self.socketio_path)

        self.name = '%s %s' % (parent_name, self.subscribe_url)

        self.ws = None
        self.ws_thread = None
        self.ping_thread = None
        self.sid = None
        self.ping_interval = None
        self.ping_timeout = None

        self.subscribed_channels = set()
        self.lock = threading.RLock()

        self.start_ws()

    def cleanup(self):
        """ Stops any threads and closes any sockets, in preparation
        for shutdown. """

        for channel_name in self.subscribed_channels:
            print("Cleaning up %s on %s:%s" % (channel_name, self.sid, self.subscribe_url))
        self.subscribed_channels = set()

        self.__stop_ping()
        self.stop_ws()

    def subscribe_channels(self, *channels):
        """ Subscribes to one or more channels for notifications.
        Parameters consist of one or more strings that represent
        channel names. """

        if not channels:
            # No-op.
            return

        with self.lock:
            if not self.sid:
                # We're not fully started up yet.  Just add it to the
                # set, it will get subscribed later.
                for channel_name in channels:
                    print("Deferring subscription to %s" % (channel_name))
                    self.subscribed_channels.add(channel_name)
                return

            # It's possible that we've just lost the websocket
            # connection, and self.sid is no longer valid, but the
            # thread hasn't cleared self.sid to None yet.  In that
            # case the below operation will fail.
            subscribe_params = {
                'user' : self.bga.user_id,
                'name' : self.bga.user_name,
                'credentials' : self.bga.socketio_credentials,
                'EIO' : self.eio,
                'transport' : 'polling',
                'sid' : self.sid,
                }

            subscribe_messages = []
            for channel_name in channels:
                subscribe_messages.append((self.notification_msgid, ["join", channel_name]))
            subscribe_text = self.format_messages(subscribe_messages)
            #print(subscribe_text)

            r = self.bga.session.post(self.subscribe_url, params = subscribe_params, data = subscribe_text)
            #print(r.url)
            if r.status_code != 200:
                message = "Unable to subscribe to topics: %s" % (r.url)
                print(r.url)
                print(r.text)

                # As described above, perhaps we only failed because
                # we happened to get called at the wrong time, just
                # when the socket is being reset.  We could perhaps
                # protect against this case by not raising an
                # exception in the case of self.auto_restart being
                # true, assuming that when the socket restarts, the
                # subscribe request will succeed.  Not sure whether
                # that's a good idea or not.
                raise RuntimeError(message)

            for channel_name in channels:
                print("Subscribed to %s on %s:%s" % (channel_name, self.sid, self.subscribe_url))
                self.subscribed_channels.add(channel_name)

        #print(r.text)

    def format_messages(self, messages):
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
        notification response.  If the response isn't of the
        expected form, returns None.  """

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
                # The response doesn't include the expected form.
                # Probably the realtime server is temporarily down.
                print('Unexpected response from BGA at position %s')
                print(text)
                return None

            length, id = m.groups()
            length = int(length)
            id = int(id)

            # The next character after the id is the beginning of the
            # message data.
            data_start = m.end(2)

            # The end of the message data is measured from the start
            # of id.
            data_end = m.start(2) + length
            assert(data_end <= len(text))

            json_text = text[data_start : data_end].strip()
            if json_text:
                try:
                    json_data = json.loads(json_text)
                except json.decoder.JSONDecodeError:
                    message = "Invalid JSON text: %s" % (json_text)
                    raise RuntimeError(message)
            else:
                json_data = None
            messages.append((id, json_data))
            p = data_end

        return messages

    def __ws_message(self, ws, text):
        """ A new message has come in on the websocket.  This method
        is called in the ws thread (I think).  Decode the message and
        dispatch it appropriately. """

        try:
            #print("Got message on %s:%s" % (self.sid, self.subscribe_url))

            # Get the integer message_id from the beginning of the message.
            pattern = re.compile('([0-9]+)')
            m = pattern.match(text)

            if m is None:
                message = 'Unexpected message from BGA: %s' % (text)
                raise RuntimeError(message)

            msgid = int(m.group(1))

            # The next character after the id is the beginning of any
            # auxiliary message data.
            data_start = m.end(1)
            data_text = text[data_start:]

            if msgid == self.server_ping_msgid:
                if data_text == self.msg_probe:
                    # When the server sends us a probe, we should send back
                    # a probe_response, and start pinging.
                    self.send_message(self.client_probe_response_msgid)
                    if not self.ping_thread:
                        self.__start_ping()
            elif msgid == self.notification_msgid:
                # Here comes a notification on one of our subscribed
                # channels.  The data will be json-encoded.
                data = json.loads(data_text)
                self.__raw_notification_received(data)

            else:
                print("Unhandled message id %s %s" % (msgid, text))

        except:
            message = "Exception in message handler"
            print(message)
            traceback.print_exc()
            raise RuntimeError(message)

    def __raw_notification_received(self, notification_data):
        message_type, message_data = notification_data
        if message_type == 'bgamsg':
            # 'bgamsg' messages have a payload which might or might
            # not be further json-encoded.
            if isinstance(message_data, str):
                bgamsg_data = json.loads(message_data)
            else:
                bgamsg_data = message_data
            channel_name = bgamsg_data['channel']
            self.bgamsg_notification_received(channel_name, bgamsg_data)

        elif message_type == 'join':
            # 'join' messages just include a channel name.  Do we need
            # to do anything else with this, or is this just a
            # notification?
            channel_name = message_data
            print("Join channel %s" % (channel_name))

        elif message_type == 'requestSpectators':
            # 'requestSpectators' messages include a table_id.  Again,
            # not sure if we need to do anything with this message.
            table_id = int(message_data)
            print("requestSpectators %s" % (table_id))

        else:
            print("Unhandled message type %s from BGA: %s" % (message_type, message_data))

    def bgamsg_notification_received(self, channel_name, message_data):
        #print("thread notification on %s: %s" % (channel_name, data))
        self.notification_queue.add_message(self.message_callback, channel_name, message_data)

    def __ws_error(self, ws, error):
        print("Socket error on %s:%s: %s" % (self.sid, self.subscribe_url, error))

        # Maybe closing the socket when we get an error notification
        # is a good idea, to help us exit cleanly?
        ws = self.ws
        if ws:
            ws.close()
            self.ws = None

    def __ws_close(self, ws, close_status_code, close_msg):
        #print("__ws_close(%s)" % (ws))
        if ws == self.ws:
            self.ws = None

        self.__stop_ping()

    def __ws_open(self, ws):
        #print("__ws_open(%s) vs. %s" % (ws, self.ws))

        self.send_message(self.client_ping_msgid, self.msg_probe)

    def send_message(self, msgid, data = None):
        """ Formats the indicated msgid (and optional data) to the
        server. """

        if data is None:
            text = '%d' % (msgid)
        elif isinstance(data, str):
            text = '%d%s' % (msgid, data)
        else:
            json_text = json.dumps(data)
            text = '%d%s' % (msgid, json_text)

        #print("send %s" % (repr(text)))
        ws = self.ws
        if ws:
            ws.send(text)
        else:
            print("Unable to send message, socket is closed")

    def start_ws(self):
        """ Open a websocket connection and start the ws thread to
        monitor it. """

        assert not self.ws
        assert not self.ws_thread

        thread_name = 'Websocket thread %s' % (self.name)
        self.ws_thread = threading.Thread(target = self.__ws_thread_main, name = thread_name)
        self.ws_thread.start()

    def stop_ws(self):
        """ Close the websocket and thread previously created by
        start_ws(). """

        # This means we want to disable auto_restart.
        self.auto_restart = False

        if not self.ws and not self.ws_thread:
            # No-op: already closed.
            return

        # This should wake up the thread.
        ws = self.ws
        if ws:
            ws.close()
            self.ws = None
            del ws

        thread = self.ws_thread
        self.ws_thread = None
        if thread:
            thread.join(self.thread_join_timeout)
            if thread.is_alive():
                print("ws_thread did not shut down for %s:%s" % (self.sid, self.subscribe_url))

    def __ws_thread_main(self):
        # Most of the work is done in __ws_thread_one_pass(), which
        # connects and listens until the socket is disconnected.

        #print ("Opening %s:%s, restart = %s" % (self.sid, self.subscribe_url, self.auto_restart))
        self.__ws_thread_one_pass()

        # As long as self.auto_restart is True, we will automatically
        # reconnect and continue to listen.
        while self.auto_restart:
            print("Waiting %s seconds to try again." % (self.restart_wait_seconds))
            time.sleep(self.restart_wait_seconds)
            print ("Retrying %s" % (self.subscribe_url))
            self.__ws_thread_one_pass()

    def __ws_thread_one_pass(self):
        """ Connect the websocket and listen for messages until we get
        disconnected for whatever reason. """

        with self.lock:
            # First, get a session ID (sid) so we can open a websocket
            # and subscribe to topics for that websocket.  We do all
            # this with the lock held, so we don't have a race
            # condition with subscribing to new channels.
            assert not self.sid
            subscribe_params = {
                'user' : self.bga.user_id,
                'name' : self.bga.user_name,
                'credentials' : self.bga.socketio_credentials,
                'EIO' : self.eio,
                'transport' : 'polling',
                }

            r = self.bga.retry_get(self.subscribe_url, params = subscribe_params)
            #print(r.url)
            messages = dict(self.parse_messages(r.text))
            if messages is None:
                # That didn't work, probably the realtime server was
                # down.
                return

            #print(messages)

            comm_protocol = messages[0]
            self.sid = comm_protocol['sid']

            # The server also tells us how frequently it will expect a
            # ping from us.  We need to respect that, or it will drop the
            # connection.
            self.ping_interval = int(comm_protocol['pingInterval']) # time in ms
            self.ping_timeout = int(comm_protocol['pingTimeout']) #?

            # Now open the new websocket.
            assert not self.ws
            websocket_params = {
                'user' : self.bga.user_id,
                'name' : self.bga.user_name,
                'credentials' : self.bga.socketio_credentials,
                'EIO' : self.eio,
                'transport' : 'websocket',
                'sid' : self.sid,
                }

            parser = requests.PreparedRequest()
            parser.prepare_url(url = self.subscribe_url, params = websocket_params)

            # Change the url in subscribe_url from https:// to wss://.
            assert(parser.url.startswith('https://'))
            url = 'wss' + parser.url[5:]
            #print(url)

            #websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(url,
                                             on_open = self.__ws_open,
                                             on_message = self.__ws_message,
                                             on_error = self.__ws_error,
                                             on_close = self.__ws_close)

            # Now, re-subscribe to whatever channels we had subscribed
            # to before, e.g. from a previous session.
            channels = list(self.subscribed_channels)
            self.subscribed_channels = set()
            self.subscribe_channels(*channels)

        # Now run and listen on the socket for incoming messages.

        # Actually, this doesn't seem to run *forever*, just until the
        # socket is closed.  That's why we have self.auto_restart.
        ws = self.ws
        if ws:
            ws.run_forever(sslopt = {"cert_reqs" : ssl.CERT_NONE})

        # There is a tiny race condition here: after the socket closes
        # (or even before we've detected that it's closing), and
        # before we set self.sid to None, some other thread might call
        # subscribe_channels() with the now-invalid self.sid, and that
        # will fail.  See subscribe_channels().
        sid = self.sid
        self.sid = None
        self.ws = None
        print ("Socket closed on %s:%s" % (sid, self.subscribe_url))

    def __start_ping(self):
        """ Starts the ping thread to send regular heartbeats to the
        BGA server so it won't hang up on us. """

        if self.ping_thread:
            # No-op, already started.
            return

        thread_name = 'Ping thread %s' % (self.name)
        self.ping_thread = threading.Thread(target = self.__ping_thread_main, name = thread_name)
        self.ping_thread.start()

    def __stop_ping(self):
        """ Stops the ping thread that was started previously. """

        if self.ping_thread:
            thread = self.ping_thread
            self.ping_thread = None
            thread.join(self.thread_join_timeout)
            if thread.is_alive():
                print("ping_thread did not shut down for %s:%s" % (self.sid, self.subscribe_url))

    def __ping_thread_main(self):
        while self.ping_thread:
            self.send_message(self.client_ping_msgid)

            # Sleep a little at a time instead of all at once, so
            # we can notice if we've been stopped by the parent.
            sleep_time = self.ping_interval / 1000.0
            stop_time = time.time() + sleep_time
            while time.time() < stop_time and self.ping_thread:
                time.sleep(0.5)
