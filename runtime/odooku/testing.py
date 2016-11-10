from odooku.wsgi import WSGIServer
import gevent

import logging


_logger = logging.getLogger(__name__)


class TestServer(WSGIServer):

    def _load_registry(self):
        _logger.info("Starting tests")
        super(TestServer, self).load_registry()
        _logger.info("Finished tests: %s failures", self._registry._assertion_report.failures)

    def load_registry(self):
        gevent.spawn(self._load_registry)
