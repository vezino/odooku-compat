import os
import click

from odooku.wsgi import WSGIServer
from odooku.utils import prefix_envvar
from werkzeug._reloader import run_with_reloader

try:
    from newrelic import agent as newrelic_agent
except ImportError:
    newrelic_agent = None


__all__ = [
    'wsgi'
]


@click.command()
@click.argument('port', nargs=1, type=int)
@click.option(
    '--timeout',
    default=25,
    envvar=prefix_envvar('TIMEOUT'),
    type=click.INT,
    help="Longpolling timeout"
)
@click.option(
    '--cdn',
    is_flag=True,
    envvar=prefix_envvar('CDN'),
    help="Enables Content Delivery through S3 endpoint or S3 custom domain."
)
@click.option(
    '--dev',
    is_flag=True,
    envvar=prefix_envvar('DEV')
)
@click.pass_context
def wsgi(ctx, port, timeout, cdn, dev):
    debug, config, params, logger = (
        ctx.obj['debug'],
        ctx.obj['config'],
        ctx.obj['params'],
        ctx.obj['logger']
    )

    # Patch odoo config, since we run with gevent
    # we do not need multiple workers, but Odoo needs
    # the fooled.
    config['workers'] = 3
    config['dev_mode'] = dev

    # Initialize newrelic_agent
    global newrelic_agent
    if newrelic_agent and any(key in os.environ for key in [
                'NEW_RELIC_LICENSE_KEY',
                'NEW_RELIC_CONFIG_FILE'
            ]):

        newrelic_agent.initialize()
    else:
        newrelic_agent = None

    # Keep track of custom config params
    params.TIMEOUT = timeout
    params.CDN_ENABLED = cdn

    def serve():
        server = WSGIServer(port, newrelic_agent=newrelic_agent)
        server.serve_forever()

    if dev:
        logger.warning("Running in development mode")
        run_with_reloader(serve)
    else:
        serve()
