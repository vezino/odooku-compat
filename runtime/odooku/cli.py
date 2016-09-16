import click
import urlparse
import os

from odooku.params import params
from odooku.utils import prefix_envvar


@click.group()
@click.option(
    '--database-url',
    required=True,
    envvar="DATABASE_URL",
    help="[database type]://[username]:[password]@[host]:[port]/[database name]"
)
@click.option(
    '--database-maxconn',
    default=6, # 20 / 3
    envvar=prefix_envvar("DATABASE_MAXCONN"),
    type=click.INT,
    help="""
    Maximum number of database connections per worker.
    See Heroku Postgres plans.
    """
)
@click.option(
    '--redis-url',
    envvar="REDIS_URL",
    help="redis://[password]@[host]:[port]/[database number]"
)
@click.option(
    '--redis-maxconn',
    default=6, # 20 / 3
    envvar=prefix_envvar("REDIS_MAXCONN"),
    type=click.INT,
    help="""
    Maximum number of redis connections per worker.
    See Heroku Redis plans.
    """
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
    '--s3-endpoint-url',
    envvar="S3_ENDPOINT_URL",
    help="S3 endpoint url."
)
@click.option(
    '--s3-custom-domain',
    envvar="S3_CUSTOM_DOMAIN",
    help="S3 custom domain."
)
@click.option(
    '--addons',
    required=True,
    envvar=prefix_envvar('ADDONS')
)
@click.option(
    '--demo-data',
    is_flag=True,
    envvar=prefix_envvar('DEMO_DATA')
)
@click.option(
    '--admin-password',
    envvar=prefix_envvar('ADMIN_PASSWORD'),
    help="Odoo admin password."
)
@click.option(
    '--debug',
    is_flag=True,
    envvar=prefix_envvar('DEBUG')
)
@click.option(
    '--dev',
    is_flag=True,
    envvar=prefix_envvar('DEV')
)
@click.option(
    '--statsd-host',
    envvar=prefix_envvar('STATSD_HOST')
)
@click.pass_context
def main(ctx, database_url, database_maxconn, redis_url, redis_maxconn,
        aws_access_key_id, aws_secret_access_key, s3_bucket, s3_endpoint_url,
        s3_custom_domain,
        addons, demo_data, admin_password, debug, dev, statsd_host):

    import odooku.logger
    odooku.logger.setup(debug=debug, statsd_host=statsd_host)

    # Setup S3
    import odooku.s3
    odooku.s3.configure(
        bucket=s3_bucket,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=s3_endpoint_url,
        custom_domain=s3_custom_domain
    )

    # Setup Redis
    import odooku.redis
    redis_url = urlparse.urlparse(redis_url) if redis_url else None
    odooku.redis.configure(
        host=redis_url.hostname if redis_url else None,
        port=redis_url.port if redis_url else None,
        password=redis_url.password if redis_url else None,
        db_number=redis_url.path[1:] if redis_url and redis_url.path else None,
        maxconn=redis_maxconn
    )

    import openerp
    # Even if 1 worker is running, we can still be running multiple
    # heroku instances.
    openerp.multi_process = True

    # Patch odoo config
    from openerp.tools import config
    database_url = urlparse.urlparse(database_url)
    database_qs = urlparse.parse_qs(database_url.query)
    config.parse_config()
    db_name = database_url.path[1:] if database_url.path else ''
    config['addons_path'] = addons
    config['db_name'] = db_name
    config['db_user'] = database_url.username
    config['db_password'] = database_url.password
    config['db_host'] = database_url.hostname
    config['db_port'] = database_url.port
    config['db_maxconn'] = database_maxconn
    config['db_sslrootcert'] = database_qs.get('sslrootcert')
    config['db_sslmode'] = database_qs.get('sslmode', 'require' if database_qs.get('sslrootcert') else None)

    config['demo'] = {}
    config['without_demo'] = 'all' if not demo_data else ''
    config['admin_passwd'] = admin_password
    config['debug'] = debug
    config['dev_mode'] = dev
    config['list_db'] = not bool(db_name)

    import logging
    logger = logging.getLogger(__name__)

    ctx.obj.update({
        'debug': debug,
        'dev': dev,
        'config': config,
        'params': params,
        'logger': logger,
    })


import odooku.commands
for name in dir(odooku.commands):
    member = getattr(odooku.commands, name)
    if isinstance(member, click.BaseCommand):
        main.add_command(member)


def entrypoint():
    main(obj={})


if __name__ == '__main__':
    main(obj={})
