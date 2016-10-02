from gunicorn.app.base import BaseApplication

from werkzeug.debug import DebuggedApplication

import sys
import math
import logging
import resource


_logger = logging.getLogger(__name__)

_memory_threshold = None



class WSGIServer(BaseApplication):

    def __init__(
            self,
            port,
            workers=3,
            threads=20,
            interface='0.0.0.0',
            worker_class='gthread',
            logger_class='odooku.logger.GunicornLogger',
            newrelic_agent=None,
            memory_threshold=None,
            **options):

        global _memory_threshold
        self.options = dict(
            bind='%s:%s' % (interface, port),
            workers=workers,
            threads=threads,
            worker_class=worker_class,
            logger_class=logger_class,
            # Preloading is not desired.
            preload_app=False
        )

        self.options.update(options)
        self._newrelic_agent = newrelic_agent

        if memory_threshold:
            # Divide accross the amount of workers minus the memory
            # in use by the main process.
            memory_threshold *= 1024
            memory_threshold -= resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_threshold = int(math.floor((memory_threshold / workers)))

        _memory_threshold = memory_threshold

        super(WSGIServer, self).__init__()

    @staticmethod
    def _post_request(worker, req, environ, resp):
        memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        _logger.debug("Memory used: %s (kb)" % memory_used)
        if _memory_threshold and memory_used > _memory_threshold:
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
        for key, value in self.options.iteritems():
            self.cfg.set(key, value)

    def load(self):
        global _memory_threshold

        _logger.info("Loading Odoo WSGI application")
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

        if _memory_threshold:
            memory_used = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            _logger.info("Memory threshold status: %s/%s (kb)" % (memory_used, _memory_threshold))
            if memory_used > _memory_threshold:
                _logger.critical("Memory threshold exceeded during load, disabling threshold")
                _memory_threshold = None
        return application


class WSGIApplicationWrapper(object):

    def __init__(self, application):
        self._application = application

    def __call__(self, environ, start_response):
        res = self._application(environ, start_response)
        return res
