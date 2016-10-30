import click

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
    config = (
        ctx.obj['config']
    )

    if module:
        modules = {
            module_name: 1
            for module_name in module
        }
        config['init'] = dict(modules)

    config['without_demo'] = '' # Enables demo data
    config['test_enable'] = True

    from openerp.tests.common import PORT, HOST
    from odooku.testing import TestServer
    server = TestServer(
        PORT,
        interface=HOST,
        workers=1,
        threads=10,
        timeout=30
    )

    server.run()
