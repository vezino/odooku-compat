from logging.config import dictConfig

import sys

from gunicorn.glogging import Logger


class GunicornLogger(Logger):

    def setup(self, cfg):
        pass


def setup_logger(debug=False):
    dictConfig(dict(
        version=1,
        disable_existing_loggers=True,
        loggers={
            'gunicorn.error': {
                'level': 'DEBUG',
                'handlers': ['error_console'],
                'qualname': 'gunicorn.error'
            },
            'gunicorn.access': {
                'level': 'DEBUG',
                'handlers': ['console'],
                'qualname': 'gunicorn.access'
            },
            '': {
                'level': 'DEBUG',
                'handlers': ['console']
            },
        },
        handlers={
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'generic',
                'stream': sys.stdout
            },
            'error_console': {
                'class': 'logging.StreamHandler',
                'formatter': 'generic',
                'stream': sys.stderr
            },
        },
        formatters={
            'generic': {
                'format': '%(asctime)s [%(process)d] [%(name)s] [%(levelname)s] %(message)s',
                'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
                'class': 'logging.Formatter'
            }
        }
    ))
