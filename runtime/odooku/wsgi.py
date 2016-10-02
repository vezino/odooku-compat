import gunicorn.app.base
from werkzeug.debug import DebuggedApplication

import logging
import resource


_logger = logging.getLogger(__name__)


class WSGIServer(gunicorn.app.base.BaseApplication):

    def __init__(
            self,
            port,
            workers=3,
            threads=20,
            interface='0.0.0.0',
            worker_class='gthread',
            logger_class='odooku.logger.GunicornLogger',
            newrelic_agent=None,
            profile_memory=False,
            **options):

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
        self._profile_memory = profile_memory
        super(WSGIServer, self).__init__()

    @staticmethod
    def _worker_abort(worker):
        pass

    def load_config(self):
        _logger.info("Gunicorn config:\n%s" % "\n".join([
            "%s: %s" % (key, val) for (key, val) in
            self.options.iteritems()
        ]))
        self.cfg.set('worker_abort', self._worker_abort)
        for key, value in self.options.iteritems():
            self.cfg.set(key, value)

    def load(self):
        _logger.info("Loading Odoo WSGI application")
        from openerp.service.wsgi_server import application
        from openerp.tools import config

        # Load addons before handling requests
        from odooku.http import Root
        import openerp.http
        root = Root()
        root.preload()
        openerp.http.root = root

        if self._profile_memory:
            application = MemoryProfilerWrapper(application)
            _logger.warning("Memory profiler enabled, do not use in production")
        
        if self._newrelic_agent:
            application = self._newrelic_agent.WSGIApplicationWrapper(application)
            _logger.info("New Relic enabled")

        if config['debug_mode']:
            application = DebuggedApplication(application, evalex=True)
            _logger.warning("Debugger enabled, do not use in production")

        return application


class MemoryProfilerWrapper(object):

    def __init__(self, application):
        self._application = application

    def __call__(self, environ, start_response):
        res = self._application(environ, start_response)
        _logger.info('Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return res
