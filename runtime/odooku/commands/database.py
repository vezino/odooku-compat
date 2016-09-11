import click

from odooku.utils import prefix_envvar


__all__ = [
    'database'
]


@click.command()
@click.pass_context
@click.option(
    '--modules',
    multiple=True,
    default=['web'],
    envvar=prefix_envvar('PRELOAD')
)
@click.option(
    '--new-dbuuid',
    is_flag=True
)
def preload(ctx, modules, new_dbuuid):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
    registry = RegistryManager.new(config['db_name'], False, None, update_module=True)
    if new_dbuuid:
        with Environment.manage():
            with registry.cursor() as cr:
                registry['ir.config_parameter'].init(cr, force=True)




@click.group()
@click.pass_context
def database(ctx):
    pass


database.add_command(preload)
