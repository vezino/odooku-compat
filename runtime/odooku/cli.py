import click
import urlparse


from odooku.params import params

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
    '--redis-url',
    envvar="REDIS_URL",
    help="redis://[password]@[host]:[port]/[database number]"
)
@click.option(
    '--aws-access-key-id',
    envvar="AWS_ACCESS_KEY_ID",
    help="Your AWS access key id."
)
@click.option(
    '--aws-secret-access-key',
    envvar="AWS_SECRET_ACCESS_KEY",
    help="Your AWS secret access key."
)
@click.option(
    '--s3-bucket',
    envvar="S3_BUCKET",
    help="S3 bucket for filestore."
)
@click.option(
    '--s3-dev-url',
    envvar="S3_DEV_URL",
    help="S3 development url."
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
@click.option(
    '--dev',
    is_flag=True,
    envvar=_prefix_envvar('DEV')
)
@click.pass_context
def main(ctx, database_url, database_maxconn, redis_url,
        aws_access_key_id, aws_secret_access_key, s3_bucket, s3_dev_url,
        addons, demo_data, debug, dev):

    from odooku.logger import setup_logger
    setup_logger(debug=debug)

    # Setup S3
    import odooku.s3
    odooku.s3.configure(
        bucket=s3_bucket,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        dev_url=s3_dev_url
    )

    # Setup Redis
    import odooku.redis
    redis_url = urlparse.urlparse(redis_url) if redis_url else None
    odooku.redis.configure(
        host=redis_url.hostname if redis_url else None,
        port=redis_url.port if redis_url else None,
        password=redis_url.password if redis_url else None,
        db_number=redis_url.path[1:] if redis_url else None
    )

    import openerp
    # Even if 1 worker is running, we can still be running multiple
    # heroku instances.
    openerp.multi_process = True

    # Patch odoo config
    from openerp.tools import config
    database_url = urlparse.urlparse(database_url)
    config.parse_config()
    config['addons_path'] = addons
    config['db_name'] = database_url.path[1:]
    config['db_user'] = database_url.username
    config['db_password'] = database_url.password
    config['db_host'] = database_url.hostname
    config['db_port'] = database_url.port
    config['db_maxconn'] = database_maxconn

    config['without_demo'] = 'all' if not demo_data else ''
    config['debug'] = debug
    config['dev_mode'] = dev
    config['list_db'] = False

    ctx.obj.update({
        'debug': debug,
        'dev': dev,
        'config': config
    })

    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("Odoo modules at:\n%s" %  "\n".join(openerp.modules.module.ad_paths))

    if dev:
        _logger.warning("RUNNING IN DEVELOPMENT MODE")

    if debug:
        _logger.warning("RUNNING IN DEBUG MODE")


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
@click.option(
    '--timeout',
    default=30,
    envvar='TIMEOUT',
    type=click.INT,
    help="Request timeout."
)
@click.pass_context
def wsgi(ctx, port, workers, threads, timeout):
    debug, dev, config = (
        ctx.obj['debug'],
        ctx.obj['dev'],
        ctx.obj['config']
    )

    # Patch odoo config
    config['workers'] = workers

    # Keep track of custom config params
    params.TIMEOUT = timeout
    extra_options = {}
    if dev:
        extra_options['reload'] = True

    from odooku.wsgi import WSGIServer
    server = WSGIServer(
        port,
        workers=workers,
        threads=threads,
        timeout=timeout,
        **extra_options
    )
    server.run()

@click.command()
@click.pass_context
@click.option(
    '--workers', '-w',
    default=2,
    envvar='WORKERS',
    type=click.INT,
    help="Number of cron workers to run."
)
@click.option(
    '--once',
    is_flag=True,
    envvar=_prefix_envvar('CRON_ONCE')
)
def cron(ctx, workers, once):
    config = (
        ctx.obj['config']
    )

    import odooku.cron
    if once:
        odooku.cron.run_once()
    else:
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
    config = (
        ctx.obj['config']
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
