import sys
import logging
import socket

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


class GunicornLogger(OdookuLogger, BaseGunicornLogger):

    def setup(self, cfg):
        # Do not setup, this will override our logging config
        pass

    def critical(self, msg, *args, **kwargs):
        super(GunicornLogger, self).critical(msg, *args, **kwargs)
        self.increment("gunicorn.log.critical", 1)

    def error(self, msg, *args, **kwargs):
        super(GunicornLogger, self).error(msg, *args, **kwargs)
        self.increment("gunicorn.log.error", 1)

    def warning(self, msg, *args, **kwargs):
        super(GunicornLogger, self).warning(msg, *args, **kwargs)
        self.increment("gunicorn.log.warning", 1)

    def exception(self, msg, *args, **kwargs):
        super(GunicornLogger, self).exception(msg, *args, **kwargs)
        self.increment("gunicorn.log.exception", 1)

    def access(self, resp, req, environ, request_time):

        # Metrics
        duration_in_ms = request_time.seconds * 1000 + float(request_time.microseconds) / 10 ** 3
        status = resp.status
        if isinstance(status, str):
            status = int(status.split(None, 1)[0])

        self.histogram("gunicorn.request.duration", duration_in_ms)
        self.increment("gunicorn.requests", 1)
        self.increment("gunicorn.request.status.%d" % status, 1)

        # Regular logging
        safe_atoms = self.atoms_wrapper_class(self.atoms(resp, req, environ,
            request_time))

        try:
            super(GunicornLogger, self).info(self.cfg.access_log_format % safe_atoms)
        except:
            super(GunicornLogger, self).error(traceback.format_exc())


def setup(debug=False, statsd_host=None):
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

    OdookuLogger._statsd_host = statsd_host
    logging.setLoggerClass(OdookuLogger)
    logging.addLevelName(25, 'INFO')

    # Prevent odoo from overriding log config
    import openerp.netsvc
    openerp.netsvc._logger_init = True
