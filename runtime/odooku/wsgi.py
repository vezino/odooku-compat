import gunicorn.app.base

import logging

_logger = logging.getLogger(__name__)


class WSGIServer(gunicorn.app.base.BaseApplication):

    def __init__(
            self,
            port,
            workers=3,
            threads=2,
            interface='0.0.0.0',
            worker_class='gthread',
            logger_class='odooku.logger.GunicornLogger',
            **options):

        self.options = dict(
            bind='%s:%s' % (interface, port),
            workers=workers,
            threads=threads,
            worker_class=worker_class,
            logger_class=logger_class
        )

        self.options.update(options)
        super(WSGIServer, self).__init__()

    @staticmethod
    def _worker_abort(worker):
        pass

    @staticmethod
    def _post_fork(server, worker):
        # Load addons before handling requests
        from openerp.http import root
        root.load_addons()
        root._loaded = True

    def load_config(self):
        _logger.info("Gunicorn config %s" % self.options)
        self.cfg.set('post_fork', self._post_fork)
        self.cfg.set('worker_abort', self._worker_abort)
        for key, value in self.options.iteritems():
            self.cfg.set(key, value)

    def load(self):
        _logger.info("Loading Odoo WSGI application")
        from openerp.service.wsgi_server import application
        return application
