import click

from odooku.utils import prefix_envvar


__all__ = [
    'cron'
]


@click.command()
@click.pass_context
@click.option(
    '--workers', '-w',
    default=2,
    envvar=prefix_envvar('WORKERS'),
    type=click.INT,
    help="Number of cron workers to run."
)
@click.option(
    '--once',
    is_flag=True,
    envvar=prefix_envvar('CRON_ONCE')
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
