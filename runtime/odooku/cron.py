from pistil.pool import PoolArbiter
from pistil.worker import Worker

import time
import openerp
from openerp.tools import config

import logging

_logger = logging.getLogger(__name__)


class CronWorker(Worker):

    def on_init(self, conf):
        self.db_index = 0

    def _db_list(self):
        return config['db_name'].split(',')

    def handle(self):
        db_names = self._db_list()
        if len(db_names):
            self.db_index = (self.db_index + 1) % len(db_names)
            db_name = db_names[self.db_index]
            _logger.debug("Polling for jobs")

            import openerp.addons.base as base
            base.ir.ir_cron.ir_cron._acquire_job(db_name)
            openerp.modules.registry.RegistryManager.delete(db_name)

            # dont keep cursors in multi database mode
            if len(db_names) > 1:
                openerp.sql_db.close_db(db_name)
        else:
            self.db_index = 0

        time.sleep(10)


def run(workers=2, preload=None):
    conf = {
        'num_workers': workers
    }

    spec = ( CronWorker, 30, 'worker', {}, 'cron',)
    pool = PoolArbiter(conf, spec)
    pool.run()
