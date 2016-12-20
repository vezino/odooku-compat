# -*- coding: utf-8 -*-

import models

from odoo import api, models, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)


def _force_s3_storage(cr, registry):
    from odooku.s3 import pool, S3Error
    if pool:
        env = api.Environment(cr, SUPERUSER_ID, {})
        IrAttachment = env['ir.attachment']
        # We need all attachments, bypass regular search
        ids = models.Model._search(IrAttachment, [])
        for attachment in IrAttachment.browse(ids):
            exists = False
            try:
                attachment._s3_put(attachment.store_fname, content_type=attachment.mimetype)
                exists = True
            except S3Error:
                raise
            attachment.write({ 's3_exists': exists })
    else:
        _logger.warning("S3 is not enabled, dataloss for attachments is imminent")
