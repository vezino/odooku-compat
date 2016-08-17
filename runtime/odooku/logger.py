import sys
import logging
import socket
import traceback

import logging
from logging.config import dictConfig

from gunicorn.glogging import Logger as BaseGunicornLogger


METRIC_VAR = "metric"
VALUE_VAR = "value"
MTYPE_VAR = "mtype"
GAUGE_TYPE = "gauge"
COUNTER_TYPE = "counter"
HISTOGRAM_TYPE = "histogram"


class OdookuLogger(logging.Logger):

    _statsd_host = None
    _statsd_sock = None
    _statsd_prefix = ''

    def __init__(self, name=None):
        super(OdookuLogger, self).__init__(name)
        if self._statsd_host:
            try:
                host, port = self._statsd_host.split(':')
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((host, int(port)))
            except Exception:
                pass
            else:
                self._statsd_sock = sock

    def critical(self, msg, *args, **kwargs):
        self.log(logging.CRITICAL, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(logging.WARNING, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(logging.INFO, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.log(logging.DEBUG, msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.log(logging.ERROR, msg, *args, **kwargs)

    def log(self, lvl, msg, *args, **kwargs):
        try:
            extra = kwargs.get("extra", None)
            if extra is not None:
                metric = extra.get(METRIC_VAR, None)
                value = extra.get(VALUE_VAR, None)
                typ = extra.get(MTYPE_VAR, None)
                if metric and value and typ:
                    if typ == GAUGE_TYPE:
                        self.gauge(metric, value)
                    elif typ == COUNTER_TYPE:
                        self.increment(metric, value)
                    elif typ == HISTOGRAM_TYPE:
                        self.histogram(metric, value)
                    else:
                        pass
        except Exception:
            logging.Logger.warning(self, "Failed to log to statsd", exc_info=True)

        if msg:
            logging.Logger.log(self, lvl, msg, *args, **kwargs)

    def gauge(self, name, value):
        self._sock_send("{0}{1}:{2}|g".format(self._statsd_prefix, name, value))

    def increment(self, name, value, sampling_rate=1.0):
        self._sock_send("{0}{1}:{2}|c|@{3}".format(self._statsd_prefix, name, value, sampling_rate))

    def decrement(self, name, value, sampling_rate=1.0):
        self._sock_send("{0){1}:-{2}|c|@{3}".format(self._statsd_prefix, name, value, sampling_rate))

    def histogram(self, name, value):
        self._sock_send("{0}{1}:{2}|ms".format(self._statsd_prefix, name, value))

    def _sock_send(self, msg):
        try:
            if self._statsd_sock is not None:
                if isinstance(msg, unicode):
                    msg = msg.encode("ascii")
                self._statsd_sock.send(msg)
        except Exception:
            logging.Logger.warning(self, "Failed to log to statsd", exc_info=True)


class GunicornLogger(BaseGunicornLogger):

    def __init__(self, cfg):
        super(GunicornLogger, self).__init__(cfg)
        self._logger = logging.getLogger('gunicorn')

    def setup(self, cfg):
        # Do not setup, this will override our logging config
        pass

    def log(self, lvl, msg, *args, **kwargs):
        if isinstance(lvl, basestring):
            lvl = self.LOG_LEVELS.get(lvl.lower(), logging.INFO)
        self._logger.log(lvl, msg, *args, **kwarg)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)
        self._logger.increment("gunicorn.log.critical", 1)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
        self._logger.increment("gunicorn.log.error", 1)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
        self._logger.increment("gunicorn.log.warning", 1)

    def exception(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
        self._logger.increment("gunicorn.log.exception", 1)

    def access(self, resp, req, environ, request_time):
        print 'access->'
        # Metrics
        duration_in_ms = request_time.seconds * 1000 + float(request_time.microseconds) / 10 ** 3
        status = resp.status
        if isinstance(status, str):
            status = int(status.split(None, 1)[0])

        self._logger.histogram("gunicorn.request.duration", duration_in_ms)
        self._logger.increment("gunicorn.requests", 1)
        self._logger.increment("gunicorn.request.status.%d" % status, 1)

        try:
            safe_atoms = self.atoms_wrapper_class(
                self.atoms(resp, req, environ, request_time)
            )
            self.info(self.cfg.access_log_format % safe_atoms)
        except:
            self.error(traceback.format_exc())
        print '<-access'


def setup(debug=False, statsd_host=None):
    level = 'DEBUG' if debug else 'INFO'
    dictConfig(dict(
        version=1,
        disable_existing_loggers=True,
        loggers={
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

    OdookuLogger._statsd_host = statsd_host
    logging.setLoggerClass(OdookuLogger)
    logging.addLevelName(25, 'INFO')

    # Prevent odoo from overriding log config
    import openerp.netsvc
    openerp.netsvc._logger_init = True
