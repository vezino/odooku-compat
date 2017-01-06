import click
import os

__all__ = [
    'cdn'
]


_reserved = ['filestore']


@click.command()
@click.pass_context
def collect(ctx):
    logger = (
        ctx.obj['logger']
    )

    from odoo.modules import get_modules, get_module_path
    from odoo.tools.osutil import listdir
    from odooku.s3 import pool as s3_pool

    for module in get_modules():
        if module in _reserved:
            logger.warning("Module name %s clashes with a reserved key", module)
            continue
        static_dir = os.path.join(get_module_path(module), 'static')
        if os.path.exists(static_dir):
            for filename in listdir(static_dir, True):
                path = os.path.join(static_dir, filename)
                url = os.path.join(module, 'static', filename)
                logger.info("Uploading %s", url)
                s3_pool.client.upload_file(path, s3_pool.bucket, url, ExtraArgs={
                    'ACL': 'public-read'
                })


@click.group()
@click.pass_context
def cdn(ctx):
    pass


cdn.add_command(collect)
