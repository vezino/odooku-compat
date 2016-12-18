import click
import urlparse

from odooku.params import params
from odooku.utils import prefix_envvar

# Setup logger first, then import further modules
import odooku.logger
odooku.logger.setup()

import openerp
from openerp.tools import config
from odooku import redis, s3

import logging
_logger = logging.getLogger(__name__)


@click.group()
@click.option(
    '--database-url',
    required=True,
    envvar="DATABASE_URL",
    help="[database type]://[username]:[password]@[host]:[port]/[database name]"
)
@click.option(
    '--database-maxconn',
    default=20,
    envvar=prefix_envvar("DATABASE_MAXCONN"),
    type=click.INT,
    help="""
    Maximum number of database connections per worker.
    See Heroku Postgres plans.
    """
)
@click.option(
    '--redis-maxconn',
    default=20,
    envvar=prefix_envvar("REDIS_MAXCONN"),
    type=click.INT,
    help="""
    Maximum number of redis connections per worker.
    See Heroku Redis plans.
    """
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
    '--s3-addressing-style',
    envvar="S3_ADDRESSING_STYLE",
    type=click.Choice(['path', 'virtual']),
    help="S3 addressing style."
)
@click.option(
    '--addons',
    required=True,
    envvar=prefix_envvar('ADDONS')
)
@click.option(
    '--tmp-dir',
    default='/tmp/odooku',
    envvar=prefix_envvar('TMP_DIR')
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
    '--statsd-host',
    envvar=prefix_envvar('STATSD_HOST')
)
@click.pass_context
def main(ctx, database_url, database_maxconn, redis_url, redis_maxconn,
        aws_access_key_id, aws_secret_access_key, s3_bucket, s3_endpoint_url,
        s3_custom_domain, s3_addressing_style,
        addons, tmp_dir, admin_password, debug, statsd_host):


    # Setup S3
    s3.configure(
        bucket=s3_bucket,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=s3_endpoint_url,
        custom_domain=s3_custom_domain,
        addressing_style=s3_addressing_style,
    )

    # Setup Redis
    redis_url = urlparse.urlparse(redis_url) if redis_url else None
    redis.configure(
        host=redis_url.hostname if redis_url else None,
        port=redis_url.port if redis_url else None,
        password=redis_url.password if redis_url else None,
        db_number=redis_url.path[1:] if redis_url and redis_url.path else None,
        maxconn=redis_maxconn
    )


    # Even if 1 worker is running, we can still be running multiple
    # heroku instances.
    openerp.multi_process = True

    # Patch odoo config
    database_url = urlparse.urlparse(database_url)
    config.parse_config()
    db_name = database_url.path[1:] if database_url.path else ''
    config['data_dir'] = tmp_dir
    config['addons_path'] = addons
    config['db_name'] = db_name
    config['db_user'] = database_url.username
    config['db_password'] = database_url.password
    config['db_host'] = database_url.hostname
    config['db_port'] = database_url.port
    config['db_maxconn'] = database_maxconn

    config['demo'] = {}
    config['without_demo'] = 'all'
    config['admin_passwd'] = admin_password
    config['debug_mode'] = debug
    config['list_db'] = not bool(db_name)

    ctx.obj.update({
        'debug': debug,
        'config': config,
        'params': params,
        'logger': _logger
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
