from openerp.http import Root as _Root, OpenERPSession
from openerp.tools import config
from openerp.tools.func import lazy_property
from werkzeug.contrib.sessions import FilesystemSessionStore

from odooku.redis import pool as redis_pool
from odooku.session import RedisSessionStore

import logging

_logger = logging.getLogger(__name__)


class Root(_Root):

    @lazy_property
    def session_store(self):
        if redis_pool:
            _logger.info('HTTP Sessions stored in redis')
            return RedisSessionStore(session_class=OpenERPSession)
        else:
            path = config.session_dir
            _logger.info('HTTP sessions stored locally in: %s', path)
            return FilesystemSessionStore(path, session_class=OpenERPSession)

    def preload(self):
        self._loaded = True
        self.load_addons()
