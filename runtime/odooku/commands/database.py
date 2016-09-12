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
@click.option(
    '--modules',
    multiple=True,
    default=['web'],
    envvar=prefix_envvar('PRELOAD')
)
def preload(ctx, modules, new_dbuuid):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.new(config['db_name'], False, None, update_module=True)



@click.command()
@click.pass_context
def newdbuuid(ctx, modules, new_dbuuid):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
    registry = RegistryManager.new(config['db_name'], False, None)
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
@click.pass_context
def restore(ctx, db_name, s3_file):
    config = (
        ctx.obj['config']
    )

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
            db.restore_db(db_name, t.name, copy=True)
            os.unlink(t.name)


@click.group()
@click.pass_context
def database(ctx):
    pass


database.add_command(preload)
database.add_command(newdbuuid)
database.add_command(dump)
database.add_command(restore)
