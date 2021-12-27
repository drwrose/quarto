import re
import json

class BGANotificationSession:
    eio = '3'  # Don't know what this is really?

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
            'name' : self.bga.username,
            'credentials' : self.bga.socketio_credentials,
            'EIO' : self.eio,
            'transport' : 'polling',
            #'t' : 'Ntu9pqW',
            }

        r = self.bga.session.get(subscribe_url, params = subscribe_params)
        messages = self.parse_messages(r)
        self.sid = messages[0]['sid']

    def parse_messages(self, r):
        """ Returns a dictionary of parsed JSON objects by id,
        extracted from the notification response. """

        # We expect a set of messages in the form of repeated strings
        # of 99:99[json], where the first 99 is the character length
        # of [json], and the second 99 is the id.

        messages = {}

        pattern = re.compile('([0-9]+):([0-9]+)')
        p = 0
        while p < len(r.text):
            # Pull out the next message.
            m = pattern.match(r.text, p)
            if m is None:
                message = 'Unexpected response from BGA at position %s: %s' % (p, r.text)
                raise RuntimeError(message)

            length, id = m.groups()
            length = int(length)
            id = int(id)
            end = m.end(0)
            json_text = r.text[end : end + length - 1].strip()
            if json_text:
                json_data = json.loads(json_text)
            else:
                json_data = None
            messages[id] = json_data
            p = end + length - 1

        print(messages)
        return messages

    def poll(self):
        """ Should be called from time to time to do some stuff. """

        print("Polling.")
        poll_url = 'https://r2.boardgamearena.net/r/'
        poll_params = {
            'user' : self.bga.user_id,
            'name' : self.bga.username,
            'credentials' : self.bga.socketio_credentials,
            'EIO' : self.eio,
            'transport' : 'polling',
            'sid' : self.sid,
            #'t' : 'Ntu9pqW',
            }

        print(poll_params)
        r = self.bga.session.get(poll_url, params = poll_params)
        messages = self.parse_messages(r)

        #print(messages)
