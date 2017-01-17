from __future__ import absolute_import

import os
import logging

import redis

_logger = logging.getLogger(__name__)


class RedisPool(object):

    def __init__(self, host, port, password=None, db_number=None,
            maxconn=None, maxconn_timeout=None):
        self._redis_pool = redis.BlockingConnectionPool(
            host=host,
            port=port,
            password=password,
            db=db_number or 0,
            max_connections=maxconn or 50,
            timeout=maxconn_timeout or 20
        )

        self._redis_client = redis.StrictRedis(
            connection_pool=self._redis_pool
        )

    def check(self):
        return True

    @property
    def client(self):
        return self._redis_client


pool = None

def configure(host=None, port=None, **options):

    global pool
    if host and port:
        _pool = RedisPool(
            host,
            port,
            **options
        )

        if _pool.check():
            pool = _pool

    if pool:
        _logger.info("Redis enabled")
    else:
        _logger.warning("Redis disabled")
