import gevent

import openerp
import openerp.service.db
import openerp.addons.base as base

import logging

_logger = logging.getLogger(__name__)


class CronRunner(object):

    def _run_one(self):
        db_names = openerp.service.db.list_dbs(True)
        if len(db_names):
            self.db_index = (self.db_index + 1) % len(db_names)
            db_name = db_names[self.db_index]

            _logger.debug("Polling for jobs")
            base.ir.ir_cron.ir_cron._acquire_job(db_name)
            openerp.modules.registry.RegistryManager.delete(db_name)

            # dont keep cursors in multi database mode
            if len(db_names) > 1:
                openerp.sql_db.close_db(db_name)
        else:
            self.db_index = 0

    def run_forever(self):
        self.db_index = 0

    def run(self):
        pass


def run_once():
    for db_name in openerp.service.db.list_dbs(True):
        run_jobs(db_name)
        openerp.sql_db.close_db(db_name)


def run():
    conf = {
        'num_workers': workers
    }

    spec = ( CronWorker, 30, 'worker', {}, 'cron',)
    pool = PoolArbiter(conf, spec)
    pool.run()
