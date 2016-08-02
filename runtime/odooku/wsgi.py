import gunicorn.app.base

import logging

_logger = logging.getLogger(__name__)


class OdookuApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(OdookuApplication, self).__init__()

    def load_config(self):
        for key, value in self.options.iteritems():
            self.cfg.set(key, value)

    def load(self):
        return self.application


def _post_fork(server, worker):
    # Load addons before handling requests
    from openerp.http import root
    root.load_addons()
    root._loaded = True



def run(port, workers=3, threads=2, preload=None):
    # Run gunicorn with at least 2 theads per worker,
    # so that the bus can run.
    options = {
        'bind': '%s:%s' % ('0.0.0.0', port),
        'worker_class': 'gthread',
        'threads': threads,
        'workers': workers,
        'post_fork': _post_fork,
        'logger_class': 'odooku.logger.GunicornLogger',
    }

    from openerp.service.wsgi_server import application
    server = OdookuApplication(application, options)
    return server.run()
