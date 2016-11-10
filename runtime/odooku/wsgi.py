from gunicorn.app.base import BaseApplication

from werkzeug.debug import DebuggedApplication

import sys
import math
import logging
import resource


_logger = logging.getLogger(__name__)


class WSGIServer(BaseApplication):

    _memory_threshold = None

    def __init__(
            self,
            port,
            workers=3,
            timeout=300,
            interface='0.0.0.0',
            logger_class='odooku.logger.GunicornLogger',
            newrelic_agent=None,
            memory_threshold=None,
            ready_handler=None,
            **options):

        self.options = dict(
            bind='%s:%s' % (interface, port),
            workers=workers,
            timeout=timeout,
            worker_class='gevent',
            logger_class=logger_class,
            preload_app=False
        )

        # Apply additonal options / overrides
        self.options.update(options)

        # Custom options
        self._newrelic_agent = newrelic_agent
        self._ready_handler = ready_handler

        if memory_threshold:
            # Divide accross the amount of workers minus the memory
            # in use by the main process.
            memory_threshold *= 1024
            memory_threshold -= resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_threshold = int(math.floor((memory_threshold / workers)))

        # Global options (accessible by static methods)
        WSGIServer._memory_threshold = memory_threshold
        super(WSGIServer, self).__init__()

    @staticmethod
    def _post_request(worker, req, environ, resp):
        memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        _logger.debug("Memory used: %s (kb)" % memory_used)
        if WSGIServer._memory_threshold and memory_used > WSGIServer._memory_threshold:
            _logger.warning("Memory threshold exceeded")
            # Short circuit Gunicorn, by removing the timestamp file
            # for this worker. This will cause the worker process
            # to be closed by the Arbiter.
            worker.tmp.close()

    def load_config(self):
        _logger.info("Gunicorn config:\n%s" % "\n".join([
            "%s: %s" % (key, val) for (key, val) in
            self.options.iteritems()
        ]))

        self.cfg.set('post_request', self._post_request)
        if self._ready_handler:
            self.cfg.set('when_ready', self._ready_handler)

        for key, value in self.options.iteritems():
            self.cfg.set(key, value)

    def load(self):
        _logger.info("Applyling psycogreen patches")
        import psycogreen.gevent
        psycogreen.gevent.patch_psycopg()

        _logger.info("Loading Odoo WSGI application")

        self.load_registry()
        from openerp.service.wsgi_server import application
        from openerp.tools import config

        # Load addons before handling requests
        from odooku.http import Root
        import openerp.http
        root = Root()
        root.preload()
        openerp.http.root = root

        application = WSGIApplicationWrapper(application)

        if self._newrelic_agent:
            application = self._newrelic_agent.WSGIApplicationWrapper(application)
            _logger.info("New Relic enabled")

        if config['debug_mode']:
            application = DebuggedApplication(application, evalex=True)
            _logger.warning("Debugger enabled, do not use in production")

        if self._memory_threshold:
            memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            _logger.info("Memory threshold status: %s/%s (kb)" % (memory_used, self._memory_threshold))
            if memory_used > self._memory_threshold:
                _logger.critical("Memory threshold exceeded during load, disabling threshold")
                self._memory_threshold = None

        return application

    def load_registry(self):
        from openerp.modules.registry import RegistryManager
        from openerp.tools import config
        self._registry = RegistryManager.new(config['db_name'])

    def run(self):
        _logger.info("Starting Odoo WSGI server")
        super(WSGIServer, self).run()


class WSGIApplicationWrapper(object):

    def __init__(self, application):
        self._application = application

    def __call__(self, environ, start_response):
        res = self._application(environ, start_response)
        return res
