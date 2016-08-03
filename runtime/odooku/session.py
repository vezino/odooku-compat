from werkzeug.contrib.sessions import SessionStore


class RedisSessionStore(SessionStore):

    def __init__(self, session_class=None):
        super(S3SessionStore, self).__init__(session_class)
        self._session = None

    def get_session_key(self, sid):
        return sid

    def save(self, session):
        key = self.get_session_key(session.sid)
        self._session = session

    def delete(self, session):
        key = self.get_session_key(session.sid)
        self._session = None

    def get(self, sid):
        if self._session:
            return self._session
        else:
            return self.new()
