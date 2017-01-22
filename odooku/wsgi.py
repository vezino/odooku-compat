from gevent.wsgi import WSGIServer as BaseWSGIServer
from werkzeug.debug import DebuggedApplication

import odoo.http
from odoo.service.wsgi_server import application as odoo_application
from odoo.tools import config

import time
import logging
import greenlet
import gevent


_logger = logging.getLogger(__name__)


class WSGIServer(BaseWSGIServer):

    def __init__(self, port, interface='0.0.0.0', max_accept=None,
            timeout=25, newrelic_agent=None, **kwargs):

        self.max_accept = max_accept or config['db_maxconn']
        self.timeout = timeout
        super(WSGIServer, self).__init__((interface, port), self.load(
            newrelic_agent=newrelic_agent
        ), log=_logger, **kwargs)


    def load(self, newrelic_agent=None):
        _logger.info("Loading Odoo WSGI application")

        application = WSGIApplicationWrapper(odoo_application, self)
        if newrelic_agent:
            application = newrelic_agent.WSGIApplicationWrapper(application)
            _logger.info("New Relic enabled")

        if config['debug_mode']:
            application = DebuggedApplication(application, evalex=True)
            _logger.warning("Debugger enabled, do not use in production")

        return application


class WSGIApplicationWrapper(object):

    def __init__(self, application, server):
        self._application = application
        self._server = server

    def __call__(self, environ, start_response):
        return self._application(environ, start_response)
