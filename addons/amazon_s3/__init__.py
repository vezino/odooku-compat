# -*- coding: utf-8 -*-

import ir_attachment

import logging

_logger = logging.getLogger(__name__)


from openerp import SUPERUSER_ID

def _force_s3_storage(cr, registry):
    from odooku.s3 import pool, S3Error
    if pool:
        attachment = registry['ir.attachment']
        # For some reason we can't search installed attachments...
        cr.execute("SELECT id FROM ir_attachment")
        ids = [row['id'] for row in cr.dictfetchall()]
        for attach in attachment.browse(cr, SUPERUSER_ID, ids, {}):
            exists = False
            try:
                attach._s3_put(attach.store_fname, content_type=attach.mimetype)
                exists = True
            except S3Error:
                raise
            attach.write({ 's3_exists': exists })
    else:
        _logger.warning("S3 is not enabled, dataloss for attachments is imminent")
