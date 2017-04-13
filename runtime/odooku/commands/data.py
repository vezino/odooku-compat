import click
import sys


__all__ = [
    'data'
]


@click.command()
@click.option(
    '--db-name'
)
@click.option(
    '--strict',
    is_flag=True
)
@click.option(
    '--link',
    is_flag=True
)
@click.option(
    '--config-file'
)
@click.pass_context
def export(ctx, db_name, strict, link, config_file=None):
    config = (
        ctx.obj['config']
    )

    db_name = db_name or config.get('db_name', '').split(',')[0]
    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)

    from odooku.data.exporter import factory
    from odooku.data.config import DataConfig
    exporter = factory()(
        registry,
        config=config_file and DataConfig.from_file(config_file) or DataConfig.defaults(),
        link=link,
        strict=strict,
    )
    exporter.export(sys.stdout)


@click.command('import')
@click.option(
    '--db-name'
)
@click.option(
    '--fake',
    is_flag=True
)
@click.option(
    '--strict',
    is_flag=True
)
@click.option(
    '--config-file'
)
@click.pass_context
def import_(ctx, db_name, fake, strict, config_file):
    config = (
        ctx.obj['config']
    )

    db_name = db_name or config.get('db_name', '').split(',')[0]
    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)
    from odooku.data import Importer
    from odooku.data.config import DataConfig
    importer = Importer(
        registry,
        config=config_file and DataConfig.from_file(config_file) or DataConfig.defaults(),
        strict=strict,
    )
    importer.import_(sys.stdin, fake=fake)


@click.group()
@click.pass_context
def data(ctx):
    pass


data.add_command(export)
data.add_command(import_)
