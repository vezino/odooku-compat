from odooku.logger import setup_logger
setup_logger()

import openerp

# Even if 1 worker is running, we can still be running multiple
# heroku instances.
openerp.multi_process = True
