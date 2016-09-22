import click
import bpython


__all__ = [
    'shell'
]


@click.command()
@click.argument('input_file', type=click.Path(exists=True), required=False)
@click.pass_context
def shell(ctx, input_file):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
    from openerp import SUPERUSER_ID

    registry = RegistryManager.get(config['db_name'])
    with Environment.manage():
        with registry.cursor() as cr:
            uid = SUPERUSER_ID
            ctx = Environment(cr, uid, {})['res.users'].context_get()
            env = Environment(cr, uid, ctx)

            context = {
                'env': env
            }

            args = []
            if input_file is not None:
                args = [input_file]
            bpython.embed(context, args=args, banner='Odooku shell')
