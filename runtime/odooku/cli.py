import click
import urlparse

import openerp
from openerp.tools import config

import logging
_logger = logging.getLogger(__name__)

def _prefix_envvar(envvar):
    return 'ODOOKU_%s' % envvar


@click.group()
@click.option(
    '--database-url',
    required=True,
    envvar="DATABASE_URL"
)
@click.option(
    '--addons',
    required=True,
    envvar=_prefix_envvar("ADDONS")
)
@click.option(
    '--debug',
    is_flag=True,
    envvar=_prefix_envvar("DEBUG")
)
@click.pass_context
def main(ctx, database_url, addons, debug):
    database_url = urlparse.urlparse(database_url)
    config.parse_config()
    config['addons_path'] = addons
    config['db_name'] = database_url.path[1:]
    config['db_user'] = database_url.username
    config['db_password'] = database_url.password
    config['db_host'] = database_url.hostname
    config['db_port'] = database_url.port
    config['dev_mode'] = debug

    ctx.obj.update({
        'debug': debug,
    })

    _logger.info(openerp.modules.module.ad_paths)


@click.command()
@click.argument('port', nargs=1)
@click.pass_context
def wsgi(ctx, port):
    debug = (
        ctx.obj['debug']
    )

    import odooku.wsgi
    odooku.wsgi.run()


@click.command()
@click.pass_context
def worker(ctx):
    debug = (
        ctx.obj['debug']
    )

    pass


main.add_command(wsgi)
main.add_command(worker)


def entrypoint():
    main(obj={})


if __name__ == '__main__':
    main(obj={})
