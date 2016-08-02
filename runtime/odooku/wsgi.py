# Part of Odoo. See LICENSE_ODOO file for full copyright and licensing details.

import gunicorn.app.base
from gunicorn.six import iteritems

from openerp.tools import config

import logging

_logger = logging.getLogger(__name__)


class OdookuApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(OdookuApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def _post_fork(server, worker):
    # Load addons before handling requests
    from openerp.http import root
    root.load_addons()
    root._loaded = True


def run(preload=None, stop=False):
    # Run gunicorn with at least 2 theads per worker,
    # so that the bus can run.
    options = {
        'bind': '%s:%s' % ('0.0.0.0', '8000'),
        'worker_class': 'gthread',
        'threads': 2,
        'workers': 3 or config['workers'],
        'post_fork': _post_fork,
        'logger_class': 'odooku.logger.GunicornLogger',
    }

    from openerp.service.wsgi_server import application
    server = OdookuApplication(application, options)
    return server.run()
