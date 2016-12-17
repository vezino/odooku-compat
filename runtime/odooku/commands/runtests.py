import click

import gevent

from odooku.wsgi import WSGIServer
from openerp.modules.registry import RegistryManager


__all__ = [
    'runtests'
]

@click.command()
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def runtests(ctx, module):
    config, logger = (
        ctx.obj['config'],
        ctx.obj['logger'],
    )

    if module:
        modules = {
            module_name: 1
            for module_name in module
        }
        config['init'] = dict(modules)

    config['without_demo'] = '' # Enables demo data
    config['test_enable'] = True
    config['xmlrpc_port'] = 8000

    from openerp.tests.common import PORT

    server = WSGIServer(
        PORT,
        max_accept=1
    )

    gevent.spawn(server.serve_forever)
    registry = RegistryManager.new(config['db_name'])

    total = (registry._assertion_report.successes + registry._assertion_report.failures)
    failures = registry._assertion_report.failures
    logger.info("Completed (%s) tests. %s failures." % (total, failures))
    return 1 if failures else 0
