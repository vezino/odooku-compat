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
    '--spec'
)
@click.pass_context
def serialize(ctx, db_name, spec=None):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)

    from odooku.data import Serializer
    json = None
    if spec is not None:
        with open(f, 'w'):
            json = f.read()
    else:
        json = sys.stdin.read()

    serializer = Serializer(registry)
    serializer.serialize()


@click.command()
@click.option(
    '--db-name',
    callback=resolve_db_name
)
@click.pass_context
def deserialize(ctx, db_name):
    config = (
        ctx.obj['config']
    )

    from odoo.modules.registry import RegistryManager
    registry = RegistryManager.get(db_name)


@click.group()
@click.pass_context
def data(ctx):
    pass


data.add_command(serialize)
data.add_command(deserialize)
