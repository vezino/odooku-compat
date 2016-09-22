import click
import tempfile
import sys
import os

from odooku.utils import prefix_envvar


__all__ = [
    'database'
]


CHUNK_SIZE = 16 * 1024


@click.command()
@click.pass_context
def preload(ctx):
    config, modules = (
        ctx.obj['config'],
        ctx.obj['modules']
    )

    config['init'] = dict(modules)
    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.new(config['db_name'])


@click.command()
@click.pass_context
def update(ctx):
    config, modules = (
        ctx.obj['config'],
        ctx.obj['modules']
    )

    config['update'] = dict(modules)
    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.new(config['db_name'], update_module=True)


@click.command()
@click.pass_context
def newdbuuid(ctx, new_dbuuid):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
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
    from openerp.api import Environment
    from openerp.service import db
    with Environment.manage():
        with tempfile.TemporaryFile() as t:
            db.dump_db(db_name, t)
            t.seek(0)
            if s3_file:
                from odooku.s3 import pool as s3_pool
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
    from openerp.api import Environment
    from openerp.service import db
    with Environment.manage():
        with tempfile.NamedTemporaryFile(delete=False) as t:
            if s3_file:
                from odooku.s3 import pool as s3_pool
                s3_pool.client.download_fileobj(s3_pool.bucket, s3_file, t)
            else:
                # Read from stdin
                while True:
                    chunk = sys.stdin.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    t.write(chunk)
            t.close()
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
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def database(ctx, module):
    module = module or ['all']
    ctx.obj['modules'] = {
        module_name: 1
        for module_name in module
    }


database.add_command(preload)
database.add_command(update)
database.add_command(newdbuuid)
database.add_command(dump)
database.add_command(restore)
