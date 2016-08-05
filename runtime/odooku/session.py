from werkzeug.contrib.sessions import SessionStore

from odooku.redis import pool as redis_pool

import json

SESSION_TIMEOUT = 60*60*24*7 # 7 weeks in seconds


class RedisSessionStore(SessionStore):

    def __init__(self, key_template='session:%s', session_class=None):
        super(RedisSessionStore, self).__init__(session_class)
        self._key_template = key_template

    def get_session_key(self, sid):
        if isinstance(sid, unicode):
            sid = sid.encode('utf-8')
        return self._key_template % sid

    def save(self, session):
        key = self.get_session_key(session.sid)
        if redis_pool.client.set(key, json.dumps(dict(session))):
            return redis_pool.client.expire(key, SESSION_TIMEOUT)

    def delete(self, session):
        return redis_pool.client.delete(self.get_session_key(session.sid))

    def get(self, sid):
        if self.is_valid_key(sid):
            data = redis_pool.client.get(self.get_session_key(sid))
            if data:
                return self.session_class(json.loads(data), sid, False)
        return self.new()

    def list(self):
        session_keys = redis_pool.client.keys(self.key_template[:-2] + '*')
        return [s[len(self.key_template)-2:] for s in session_keys]
