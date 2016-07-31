from logging.config import dictConfig

import sys



def setup_logging(debug=False):
    dictConfig(dict(
        version=1,
        disable_existing_loggers=True,
        loggers={
            'root': {'level': 'DEBUG', 'handlers': ['console']},
            'gunicorn.error': {
                'level': 'DEBUG',
                'handlers': ['error_console'],
                'propagate': True,
                'qualname': 'gunicorn.error'
            },

            'gunicorn.access': {
                'level': 'DEBUG',
                'handlers': ['console'],
                'propagate': True,
                'qualname': 'gunicorn.access'
            }
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
                'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
                'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
                'class': 'logging.Formatter'
            }
        }
    ))
