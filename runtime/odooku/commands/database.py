import click
import tempfile
import sys
import os

from odooku.s3 import pool as s3_pool
from odooku.utils import prefix_envvar

from openerp.api import Environment
from openerp.service import db
from openerp.modules.registry import RegistryManager


__all__ = [
    'database'
]


CHUNK_SIZE = 16 * 1024


@click.command()
@click.option(
    '--module',
    multiple=True
)
@click.option(
    '--demo-data',
    is_flag=True,
    envvar=prefix_envvar('DEMO_DATA')
)
@click.pass_context
def preload(ctx, module, demo_data):
    config = (
        ctx.obj['config']
    )

    if module:
        modules = {
            module_name: 1
            for module_name in module
        }
        config['init'] = dict(modules)

    registry = RegistryManager.new(config['db_name'], force_demo=demo_data, update_module=True)


@click.command()
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def update(ctx, module):
    config = (
        ctx.obj['config']
    )

    module = module or ['all']
    modules = {
        module_name: 1
        for module_name in module
    }

    config['update'] = dict(modules)
    registry = RegistryManager.new(config['db_name'], update_module=True)


@click.command()
@click.pass_context
def newdbuuid(ctx, new_dbuuid):
    config = (
        ctx.obj['config']
    )

    registry = RegistryManager.get(config['db_name'])
    with Environment.manage():
        with registry.cursor() as cr:
            registry['ir.config_parameter'].init(cr, force=True)


@click.command()
@click.option(
    '--db-name'
)
@click.option(
    '--s3-file'
)
@click.pass_context
def dump(ctx, db_name, s3_file):
    config = (
        ctx.obj['config']
    )

    db_name = db_name or config.get('db_name', '').split(',')[0]
    with tempfile.TemporaryFile() as t:
        with Environment.manage():
            db.dump_db(db_name, t)

        t.seek(0)
        if s3_file:
            s3_pool.client.upload_fileobj(t, s3_pool.bucket, s3_file)
        else:
            # Pipe to stdout
            while True:
                chunk = t.read(CHUNK_SIZE)
                if not chunk:
                    break
                sys.stdout.write(chunk)


@click.command()
@click.option(
    '--db-name'
)
@click.option(
    '--s3-file'
)
@click.option(
    '--truncate',
    is_flag=True
)
@click.option(
    '--update',
    is_flag=True
)
@click.option(
    '--skip-pg',
    is_flag=True
)
@click.option(
    '--skip-filestore',
    is_flag=True
)
@click.pass_context
def restore(ctx, db_name, s3_file, truncate=None, update=None, skip_pg=None, skip_filestore=None):
    config = (
        ctx.obj['config']
    )

    if update:
        config['update']['all'] = 1

    db_name = db_name or config.get('db_name', '').split(',')[0]
    with tempfile.NamedTemporaryFile(delete=False) as t:
        if s3_file:
            s3_pool.client.download_fileobj(s3_pool.bucket, s3_file, t)
        else:
            # Read from stdin
            while True:
                chunk = sys.stdin.read(CHUNK_SIZE)
                if not chunk:
                    break
                t.write(chunk)
        t.close()

        with Environment.manage():
            db.restore_db(
                db_name,
                t.name,
                copy=True,
                truncate=truncate,
                update=update,
                skip_pg=skip_pg,
                skip_filestore=skip_filestore
            )

        os.unlink(t.name)


@click.group()
@click.pass_context
def database(ctx):
    pass


database.add_command(preload)
database.add_command(update)
database.add_command(newdbuuid)
database.add_command(dump)
database.add_command(restore)
