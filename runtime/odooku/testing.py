import threading

from odooku.wsgi import WSGIServer

import logging


_logger = logging.getLogger(__name__)


class TestServer(WSGIServer):

    def load_registry(self):
        _logger.info("Starting tests")
        super(TestServer, self).load_registry()
        _logger.info("FINISHED TESTS")

    def run(self):
        _logger.info("Starting Odoo test server")

        t = threading.Thread(target=self.load_registry)
        t.start()

        # Call WSGIServer's super (no typo)
        super(WSGIServer, self).run()
