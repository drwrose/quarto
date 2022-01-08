from BGANotificationSession import BGANotificationSession
from BGANotificationQueue import BGANotificationQueue

class BGANotifications:
    """ A self-contained collection of one or more
    BGANotificationSessions, listening for various asynchronous
    messages from different BGA servers. """

    def __init__(self, bga, name = None, auto_restart = False):
        self.bga = bga
        self.name = name
        self.auto_restart = auto_restart

        # The list of all BGANotificationSession objects, and the cvar
        # that is notified when a new notification comes in on one of
        # them.
        self.notification_sessions = []
        self.notification_queue = BGANotificationQueue()

    def cleanup(self):
        """ Stops and removes all previously created notification
        sessions. """

        for notification in self.notification_sessions:
            notification.cleanup()
        self.notification_sessions = []

        # Should we dispatch any still-pending messages?  Maybe not.

    def dispatch(self, block = False, timeout = None):
        """ Processes any pending messages, and dispatches them
        appropriately.  If block is True, this call will wait up to
        timeout seconds for a message to come in.  Should always be
        called from the main thread, or whatever thread serves as a
        parent thread to this object, to guarantee message
        ordering. """

        self.notification_queue.dispatch(block = block, timeout = timeout)

    def create_notification_session(self, message_callback = None, socketio_url = 'https://r2.boardgamearena.net', socketio_path = 'r'):
        """ Signs up for notifications of events from BGA. """
        notification = BGANotificationSession(self.bga, parent_name = self.name, notification_queue = self.notification_queue, message_callback = message_callback, socketio_url = socketio_url, socketio_path = socketio_path, auto_restart = self.auto_restart)
        self.notification_sessions.append(notification)
        return notification

    def close_notification_session(self, notification):
        self.notification_sessions.remove(notification)
        notification.cleanup()
