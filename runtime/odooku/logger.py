import sys
import logging
from logging.config import dictConfig

from gunicorn.glogging import Logger


LOG_LEVEL = 'INFO'


class GunicornLogger(Logger):

    def setup(self, cfg):
        pass


def setup_logger(debug=False):
    logging.addLevelName(25, 'INFO')
    dictConfig(dict(
        version=1,
        disable_existing_loggers=True,
        loggers={
            'gunicorn.error': {
                'level': LOG_LEVEL,
                'handlers': ['console'],
                'qualname': 'gunicorn.error'
            },
            'gunicorn.access': {
                'level': LOG_LEVEL,
                'handlers': ['console'],
                'qualname': 'gunicorn.access'
            },
            '': {
                'level': LOG_LEVEL,
                'handlers': ['console']
            },
        },
        handlers={
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'generic',
                'stream': sys.stdout
            }
        },
        formatters={
            'generic': {
                'format': '[%(process)d] [%(levelname)8s] %(message)s',
                'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
                'class': 'logging.Formatter'
            }
        }
    ))
