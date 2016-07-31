# Part of Odoo. See LICENSE_ODOO file for full copyright and licensing details.

import gunicorn.app.base

from gunicorn.six import iteritems

from openerp.tools import config


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
    import psycogreen.gevent
    psycogreen.gevent.patch_psycopg()
    from odooku.logs import setup_logging
    setup_logging(False)

def run(preload=None, stop=False):
    options = {
        'bind': '%s:%s' % ('0.0.0.0', '8000'),
        'worker_class': 'gevent',
        'workers': 3 or config['workers'],
        'post_fork': _post_fork,
        'loglevel': 'debug'
    }

    from openerp.service.wsgi_server import application
    server = OdookuApplication(application, options)
    return server.run()
