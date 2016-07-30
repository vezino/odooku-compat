# Part of Odoo. See LICENSE_ODOO file for full copyright and licensing details.

from __future__ import unicode_literals

import multiprocessing

import gunicorn.app.base

from gunicorn.six import iteritems


import openerp


def memory_info(process):
    """ psutil < 2.0 does not have memory_info, >= 3.0 does not have
    get_memory_info """
    pmem = (getattr(process, 'memory_info', None) or process.get_memory_info)()
    return (pmem.rss, pmem.vms)


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


#----------------------------------------------------------
# start/stop public api
#----------------------------------------------------------

server = None

def load_server_wide_modules():
    for m in openerp.conf.server_wide_modules:
        try:
            openerp.modules.module.load_openerp_module(m)
        except Exception:
            msg = ''
            if m == 'web':
                msg = """
The `web` module is provided by the addons found in the `openerp-web` project.
Maybe you forgot to add those addons in your addons_path configuration."""
            _logger.exception('Failed to load server-wide module `%s`.%s', m, msg)

def load_test_file_yml(registry, test_file):
    with registry.cursor() as cr:
        openerp.tools.convert_yaml_import(cr, 'base', file(test_file), 'test', {}, 'init')
        if config['test_commit']:
            _logger.info('test %s has been commited', test_file)
            cr.commit()
        else:
            _logger.info('test %s has been rollbacked', test_file)
            cr.rollback()

def load_test_file_py(registry, test_file):
    # Locate python module based on its filename and run the tests
    test_path, _ = os.path.splitext(os.path.abspath(test_file))
    for mod_name, mod_mod in sys.modules.items():
        if mod_mod:
            mod_path, _ = os.path.splitext(getattr(mod_mod, '__file__', ''))
            if test_path == mod_path:
                suite = unittest.TestSuite()
                for t in unittest.TestLoader().loadTestsFromModule(mod_mod):
                    suite.addTest(t)
                _logger.log(logging.INFO, 'running tests %s.', mod_mod.__name__)
                stream = openerp.modules.module.TestStream()
                result = unittest.TextTestRunner(verbosity=2, stream=stream).run(suite)
                success = result.wasSuccessful()
                if hasattr(registry._assertion_report,'report_result'):
                    registry._assertion_report.report_result(success)
                if not success:
                    _logger.error('%s: at least one error occurred in a test', test_file)

def preload_registries(dbnames):
    """ Preload a registries, possibly run a test file."""
    # TODO: move all config checks to args dont check tools.config here
    config = openerp.tools.config
    test_file = config['test_file']
    dbnames = dbnames or []
    rc = 0
    for dbname in dbnames:
        try:
            update_module = config['init'] or config['update']
            registry = RegistryManager.new(dbname, update_module=update_module)
            # run test_file if provided
            if test_file:
                _logger.info('loading test file %s', test_file)
                with openerp.api.Environment.manage():
                    if test_file.endswith('yml'):
                        load_test_file_yml(registry, test_file)
                    elif test_file.endswith('py'):
                        load_test_file_py(registry, test_file)

            if registry._assertion_report.failures:
                rc += 1
        except Exception:
            _logger.critical('Failed to initialize database `%s`.', dbname, exc_info=True)
            return -1
    return rc

def _post_fork(server, worker):
    import psycogreen.gevent
    psycogreen.gevent.patch_psycopg()

def start(preload=None, stop=False):
    config = openerp.tools.config
    options = {
        'bind': '%s:%s' % ('0.0.0.0', '8000'),
        'worker_class': 'gevent',
        'workers': 3 or config['workers'],
        'post_fork': _post_fork,
    }
    server = OdookuApplication(openerp.service.wsgi_server.application, options)
    return server.run() or 0

def restart():
    raise NotImplementedError
