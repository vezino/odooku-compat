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
    envvar="DATABASE_URL",
    help="[database type]://[username]:[password]@[host]:[port]/[database name]"
)
@click.option(
    '--database-maxconn', '-c',
    default=20,
    envvar='DATABASE_MAXCONN',
    type=click.INT,
    help="Maximum number of database connections per worker. See Heroku Postgres plans."
)
@click.option(
    '--addons',
    required=True,
    envvar=_prefix_envvar('ADDONS')
)
@click.option(
    '--demo-data',
    is_flag=True,
    envvar=_prefix_envvar('DEMO_DATA')
)
@click.option(
    '--debug',
    is_flag=True,
    envvar=_prefix_envvar('DEBUG')
)
@click.pass_context
def main(ctx, database_url, database_maxconn, addons, demo_data, debug):
    database_url = urlparse.urlparse(database_url)
    config.parse_config()
    config['addons_path'] = addons
    config['db_name'] = database_url.path[1:]
    config['db_user'] = database_url.username
    config['db_password'] = database_url.password
    config['db_host'] = database_url.hostname
    config['db_port'] = database_url.port
    config['db_maxconn'] = database_maxconn

    config['without_demo'] = not demo_data
    config['debug'] = debug
    config['list_db'] = False

    ctx.obj.update({
        'debug': debug,
    })

    _logger.info(openerp.modules.module.ad_paths)


@click.command()
@click.argument('port', nargs=1)
@click.option(
    '--workers', '-w',
    default=3,
    envvar='WORKERS',
    type=click.INT,
    help="Number of wsgi workers to run."
)
@click.option(
    '--threads', '-t',
    default=2,
    envvar='THREADS',
    type=click.INT,
    help="Number of threads per wsgi worker, should be a minimum of 2."
)
@click.pass_context
def wsgi(ctx, port, workers, threads):
    debug = (
        ctx.obj['debug']
    )

    config['workers'] = workers

    import odooku.wsgi
    odooku.wsgi.run(port, workers=workers, threads=threads)


@click.command()
@click.pass_context
@click.option(
    '--workers', '-w',
    default=2,
    envvar='WORKERS',
    type=click.INT,
    help="Number of cron workers to run."
)
def cron(ctx, workers):
    debug = (
        ctx.obj['debug']
    )

    import odooku.cron
    odooku.cron.run(workers=workers)


@click.command()
@click.pass_context
@click.option(
    '--modules',
    multiple=True,
    default=['web'],
    envvar=_prefix_envvar('PRELOAD')
)
def preload(ctx, modules):
    debug = (
        ctx.obj['debug']
    )
    
    from openerp.modules.registry import RegistryManager
    registry = RegistryManager.new(config['db_name'])


main.add_command(wsgi)
main.add_command(cron)
main.add_command(preload)


def entrypoint():
    main(obj={})


if __name__ == '__main__':
    main(obj={})
