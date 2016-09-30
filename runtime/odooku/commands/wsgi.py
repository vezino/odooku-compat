import os
import click

from odooku.utils import prefix_envvar

try:
    from newrelic import agent as newrelic_agent
except ImportError:
    newrelic_agent = None


__all__ = [
    'wsgi'
]


@click.command()
@click.argument('port', nargs=1)
@click.option(
    '--workers', '-w',
    default=3,
    envvar=prefix_envvar('WORKERS'),
    type=click.INT,
    help="Number of wsgi workers to run."
)
@click.option(
    '--threads', '-t',
    default=20,
    envvar=prefix_envvar('THREADS'),
    type=click.INT,
    help="Number of threads per wsgi worker, should be a minimum of 2."
)
@click.option(
    '--timeout',
    default=25,
    envvar=prefix_envvar('TIMEOUT'),
    type=click.INT,
    help="Request timeout. Keep it below Heroku's timeout."
)
@click.option(
    '--cdn',
    is_flag=True,
    envvar=prefix_envvar('CDN'),
    help="Enables Content Delivery through S3 endpoint or S3 custom domain."
)
@click.option(
    '--profile-memory',
    is_flag=True,
    help="Enable memory profiler for detecting memory leaks."
)
@click.pass_context
def wsgi(ctx, port, workers, threads, timeout, cdn, profile_memory):
    debug, dev, config, params = (
        ctx.obj['debug'],
        ctx.obj['dev'],
        ctx.obj['config'],
        ctx.obj['params']
    )

    # Patch odoo config
    config['workers'] = workers

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
    extra_options = {
        'newrelic_agent': newrelic_agent,
        'profile_memory': profile_memory,
        'reload': dev,
    }

    from odooku.wsgi import WSGIServer
    server = WSGIServer(
        port,
        workers=workers,
        threads=threads,
        timeout=timeout,
        **extra_options
    )
    server.run()
