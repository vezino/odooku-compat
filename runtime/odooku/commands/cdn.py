import click
import os


__all__ = [
    'cdn'
]


@click.command()
@click.pass_context
def collect(ctx):
    logger = (
        ctx.obj['logger']
    )

    import openerp.modules
    import openerp.tools
    from odooku.s3 import pool as s3_pool
    for module in openerp.modules.get_modules():
        static_dir = os.path.join(openerp.modules.get_module_path(module), 'static')
        if os.path.exists(static_dir):
            for filename in openerp.tools.osutil.listdir(static_dir, True):
                path = os.path.join(static_dir, filename)
                url = os.path.join('modules', module, 'static', filename)
                logger.info("Uploading %s", url)
                s3_pool.client.upload_file(path, s3_pool.bucket, url, ExtraArgs={
                    'ACL': 'public-read'
                })


@click.group()
@click.pass_context
def cdn(ctx):
    pass


cdn.add_command(collect)
