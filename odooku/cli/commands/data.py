import click
import sys

from odooku.cli.helpers import resolve_db_name


__all__ = [
    'data'
]


@click.command()
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.option(
    '--config-file'
)
@click.pass_context
def export(ctx, db_name, config_file=None):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)

    from odooku.data import Exporter, ExportConfig
    exporter = Exporter(
        registry,
        config=config_file and ExportConfig.from_file(config_file) or None
    )
    exporter.export()


@click.command('import')
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.pass_context
def import_(ctx, db_name):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)


@click.group()
@click.pass_context
def data(ctx):
    pass


data.add_command(export)
data.add_command(import_)
