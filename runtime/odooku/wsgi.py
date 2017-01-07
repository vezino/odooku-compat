from gevent.wsgi import WSGIServer as BaseWSGIServer
from werkzeug.debug import DebuggedApplication

import odoo.http
from odoo.service.wsgi_server import application
from odoo.tools import config

from odooku.http import Root

import time
import logging
import greenlet
import gevent


_logger = logging.getLogger(__name__)


class WSGIServer(BaseWSGIServer):

    def __init__(self, port, interface='0.0.0.0', max_accept=None,
            newrelic_agent=None, block_timeout=None):

        self.max_accept = max_accept or config['db_maxconn']
        self.block_timeout = block_timeout
        super(WSGIServer, self).__init__((interface, port), self.load(
            newrelic_agent=newrelic_agent
        ), log=_logger)

    def _greenlet_switch_tracer(self, what, (origin, target)):
        self._active_greenlet = target
        self._greenlet_switch_counter += 1

        then = self._greenlet_last_switch_time
        now = self._greenlet_last_switch_time = time.time()
        if then is not None:
            blocking_time = int(round((now - then) * 1000))
            if origin is not gevent.hub.get_hub():
                if blocking_time > self.block_timeout:
                    _logger.warning("Greenlet blocked for %s ms" % blocking_time)

    def load(self, newrelic_agent=None):
        _logger.info("Loading Odoo WSGI application")

        if self.block_timeout:
            self._active_greenlet = None
            self._greenlet_switch_counter = 0
            self._greenlet_last_switch_time = None
            greenlet.settrace(self._greenlet_switch_tracer)

        # Patch http
        root = Root()
        root.preload()
        odoo.http.root = root

        wrapped = WSGIApplicationWrapper(application, self)

        if newrelic_agent:
            wrapped = newrelic_agent.WSGIApplicationWrapper(application)
            _logger.info("New Relic enabled")

        if config['debug_mode']:
            wrapped = DebuggedApplication(application, evalex=True)
            _logger.warning("Debugger enabled, do not use in production")

        return wrapped


class WSGIApplicationWrapper(object):

    def __init__(self, application, server):
        self._application = application
        self._server = server

    def __call__(self, environ, start_response):
        res = self._application(environ, start_response)
        return res
