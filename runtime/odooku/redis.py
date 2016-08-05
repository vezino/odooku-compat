from __future__ import absolute_import

import os
import logging

from werkzeug.local import Local

import redis

_logger = logging.getLogger(__name__)


class RedisPool(object):

    def __init__(self, host, port, password=None, db_number=None):
        self._local = Local()
        self._host = host
        self._port = port
        self._password = password
        self._db_number = db_number

    def check(self):
        return True

    @property
    def client(self):
        if not hasattr(self._local, 'client'):
            self._local.client = redis.StrictRedis(
                host=self._host,
                port=self._port,
                password=self._password,
                db=self._db_number or 0
            )

        return self._local.client


pool = None

def configure(host=None, port=None, password=None, db_number=None):

    global pool
    if host and port:
        _pool = RedisPool(
            host,
            port,
            password=password,
            db_number=db_number
        )

        if _pool.check():
            pool = _pool

    if pool:
        _logger.info("Redis enabled")
    else:
        _logger.warning("Redis disabled")
