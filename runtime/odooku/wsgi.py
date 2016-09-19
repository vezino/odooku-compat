import gunicorn.app.base
from werkzeug.debug import DebuggedApplication

import logging

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
        
        if config['debug_mode']:
            application = DebuggedApplication(application, evalex=True)
        return application
