# from pistil.pool import PoolArbiter
# from pistil.worker import Worker

# import time
# import openerp
# import openerp.service.db

# import logging

# _logger = logging.getLogger(__name__)


# def run_jobs(db_name):
#     import openerp.addons.base as base
#     _logger.debug("Polling for jobs")
#     base.ir.ir_cron.ir_cron._acquire_job(db_name)
#     openerp.modules.registry.RegistryManager.delete(db_name)


# class CronWorker(Worker):

#     def on_init(self, conf):
#         self.db_index = 0

#     def handle(self):
#         db_names = openerp.service.db.list_dbs(True)
#         if len(db_names):
#             self.db_index = (self.db_index + 1) % len(db_names)
#             db_name = db_names[self.db_index]

#             run_jobs(db_name)

#             # dont keep cursors in multi database mode
#             if len(db_names) > 1:
#                 openerp.sql_db.close_db(db_name)
#         else:
#             self.db_index = 0

#         time.sleep(10)


# def run_once():
#     for db_name in openerp.service.db.list_dbs(True):
#         run_jobs(db_name)
#         openerp.sql_db.close_db(db_name)


# def run(workers=2, preload=None):
#     conf = {
#         'num_workers': workers
#     }

#     spec = ( CronWorker, 30, 'worker', {}, 'cron',)
#     pool = PoolArbiter(conf, spec)
#     pool.run()

import time
import openerp
import openerp.service.db
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

_logger = logging.getLogger(__name__)

def run_jobs(db_name):
    import openerp.addons.base as base
    _logger.debug("Polling for jobs")
    base.ir.ir_cron.ir_cron._acquire_job(db_name)
    openerp.modules.registry.RegistryManager.delete(db_name)


class CronWorker:
    def __init__(self):
        self.db_index = 0

    def handle(self):
        db_names = openerp.service.db.list_dbs(True)
        if len(db_names):
            self.db_index = (self.db_index + 1) % len(db_names)
            db_name = db_names[self.db_index]

            run_jobs(db_name)

            # Don't keep cursors in multi-database mode
            if len(db_names) > 1:
                openerp.sql_db.close_db(db_name)
        else:
            self.db_index = 0

        time.sleep(10)


def worker_task(worker):
    while True:
        worker.handle()


def run_once():
    for db_name in openerp.service.db.list_dbs(True):
        run_jobs(db_name)
        openerp.sql_db.close_db(db_name)


def run(workers=2):
    # Initialize workers
    cron_workers = [CronWorker() for _ in range(workers)]
    
    # Using ThreadPoolExecutor to manage the workers
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(worker_task, worker) for worker in cron_workers]
        
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            _logger.info("Shutting down workers...")
        except Exception as e:
            _logger.error(f"An error occurred: {e}")
        finally:
            _logger.info("Workers have been stopped.")
