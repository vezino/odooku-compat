import sys
import os
import tempfile
import click


CHUNK_SIZE = 16 * 1024


@click.command()
@click.argument('language', nargs=1)
@click.option(
    '--module',
    multiple=True
)
@click.pass_context
def export(ctx, language, module):
    config = (
        ctx.obj['config']
    )

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
    from openerp.tools import trans_export

    modules = module or ['all']
    with tempfile.TemporaryFile() as t:
        registry = RegistryManager.get(config['db_name'])
        with Environment.manage():
            with registry.cursor() as cr:
                trans_export(language, modules, t, 'po', cr)

        t.seek(0)
        # Pipe to stdout
        while True:
            chunk = t.read(CHUNK_SIZE)
            if not chunk:
                break
            sys.stdout.write(chunk)


@click.command('import')
@click.argument('language', nargs=1)
@click.option(
    '--overwrite',
    is_flag=True
)
@click.pass_context
def import_(ctx, language, overwrite):
    config = (
        ctx.obj['config']
    )

    context = {
        'overwrite': overwrite
    }

    from openerp.modules.registry import RegistryManager
    from openerp.api import Environment
    from openerp.tools import trans_load

    with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as t:
        registry = RegistryManager.get(config['db_name'])

        # Read from stdin
        while True:
            chunk = sys.stdin.read(CHUNK_SIZE)
            if not chunk:
                break
            t.write(chunk)
        t.close()

        with Environment.manage():
            with registry.cursor() as cr:
                trans_load(cr, t.name, language, context=context)

        os.unlink(t.name)



@click.group()
@click.pass_context
def trans(ctx):
    pass


trans.add_command(export)
trans.add_command(import_)
