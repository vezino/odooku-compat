from gevent.wsgi import WSGIServer as BaseWSGIServer
from werkzeug.debug import DebuggedApplication

import odoo.http
from odoo.service.wsgi_server import application
from odoo.tools import config

from odooku.http import Root

import logging


_logger = logging.getLogger(__name__)


class WSGIServer(BaseWSGIServer):

    def __init__(self, port, interface='0.0.0.0', max_accept=None,
            newrelic_agent=None, reload=False):

        self.max_accept = max_accept or config['db_maxconn']
        super(WSGIServer, self).__init__((interface, port), self.load(
            newrelic_agent=newrelic_agent
        ), log=_logger)

    def load(self, newrelic_agent=None):
        _logger.info("Loading Odoo WSGI application")

        # Patch http
        root = Root()
        root.preload()
        odoo.http.root = root

        wrapped = WSGIApplicationWrapper(application)

        if newrelic_agent:
            wrapped = newrelic_agent.WSGIApplicationWrapper(application)
            _logger.info("New Relic enabled")

        if config['debug_mode']:
            wrapped = DebuggedApplication(application, evalex=True)
            _logger.warning("Debugger enabled, do not use in production")

        return wrapped


class WSGIApplicationWrapper(object):

    def __init__(self, application):
        self._application = application

    def __call__(self, environ, start_response):
        res = self._application(environ, start_response)
        return res
