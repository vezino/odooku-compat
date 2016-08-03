import sys
import logging
from logging.config import dictConfig

from gunicorn.glogging import Logger


class GunicornLogger(Logger):

    def setup(self, cfg):
        pass

    def access(self, resp, req, environ, request_time):
        """ See http://httpd.apache.org/docs/2.0/logs.html#combined
        for format details
        """
        # wrap atoms:
        # - make sure atoms will be test case insensitively
        # - if atom doesn't exist replace it by '-'
        safe_atoms = self.atoms_wrapper_class(self.atoms(resp, req, environ,
            request_time))

        try:
            self.access_log.info(self.cfg.access_log_format % safe_atoms)
        except:
            self.error(traceback.format_exc())


def setup_logger(debug=False):
    level = 'DEBUG' if debug else 'INFO'
    dictConfig(dict(
        version=1,
        disable_existing_loggers=True,
        loggers={
            'gunicorn.error': {
                'level': level,
                'handlers': ['console'],
                'qualname': 'gunicorn.error'
            },
            'gunicorn.access': {
                'level': level,
                'handlers': ['console'],
                'qualname': 'gunicorn.access'
            },
            '': {
                'level': level,
                'handlers': ['console']
            },
        },
        handlers={
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'stream': sys.stdout
            },
        },
        formatters={
            'simple': {
                'format': '[%(process)d] [%(levelname)s] %(message)s',
                'class': 'logging.Formatter'
            },
        }
    ))

    logging.addLevelName(25, 'INFO')
