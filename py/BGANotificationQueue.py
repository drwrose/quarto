import threading
import queue
import time

class BGANotificationQueue:
    """ This is a temporary holding repository for notifications
    received from an asynchronous channel by BGANotificationSession,
    which adds notifications in a child thread; messages may be
    extracted and dispatched in a parent thread by calling
    dispatch().

    Multiple different BGANotificationSession objects share the same
    BGANotificationQueue; they may each add messages in their own
    thread. """

    def __init__(self):
        # This condition variable protects the queue, and is also
        # notified as messages are added to the queue.
        self.cvar = threading.Condition()

        # This is a queue of (callback_func, channel_name,
        # message_data), one for each message.
        self.queue = queue.Queue()

    def add_message(self, callback_func, channel_name, message_data):
        with self.cvar:
            self.queue.put((callback_func, channel_name, message_data))
            self.cvar.notify()

    def dispatch(self, block = False, timeout = None):
        """ Processes any pending messages, and dispatches them
        appropriately.  If block is True, this call will wait up to
        timeout seconds for a message to come in.  Should always be
        called from the main thread, or whatever thread serves as a
        parent thread to this object, to guarantee message
        ordering. """

        pending_messages = []
        with self.cvar:
            if block:
                if timeout is None:
                    # Wait indefinitely.
                    while self.queue.empty():
                        self.cvar.wait()
                else:
                    # Wait up till a certain amount of time.
                    stop_time = time.time() + timeout
                    wait_time = timeout
                    while self.queue.empty() and wait_time > 0:
                        self.cvar.wait(timeout = wait_time)
                        wait_time = stop_time - time.time()

            # Done waiting; extract all of the pending queue messages.
            while not self.queue.empty():
                message = self.queue.get()
                pending_messages.append(message)

        # Now that the lock is released, dispatch all of the messages
        # we might have extracted.
        for callback_func, channel_name, message_data in pending_messages:
            callback_func(channel_name, message_data, True)
