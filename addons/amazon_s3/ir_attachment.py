# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, SUPERUSER_ID
from openerp.osv import fields, osv

import os
import logging
from botocore.exceptions import ClientError
from odooku.s3 import pool as s3_pool, S3Error, S3NoSuchKey


_logger = logging.getLogger(__name__)


class ir_attachment(osv.osv):

    _inherit = 'ir.attachment'

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.store_fname:
                try:
                    result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size, attach.s3_exists)
                except S3NoSuchKey:
                    # SUPERUSER_ID as probably don't have write access, trigger during create
                    _logger.warning("Preventing further s3 (%s) lookups for '%s'", s3_pool.bucket, attach.store_fname)
                    self.write(cr, SUPERUSER_ID, [attach.id], { 's3_exists': False }, context=context)
                    result[attach.id] = ''
                except S3Error:
                    result[attach.id] = ''

                if result[attach.id] == '':
                    _logger.warning("Failed to read attachment %s/%s: %s", attach.id, attach.name, attach.datas_fname)
            else:
                result[attach.id] = attach.db_datas
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        res = super(ir_attachment, self)._data_set(cr, uid, id, name, value, arg, context=None)
        if s3_pool:
            attach = self.browse(cr, uid, id, context=context)
            s3_exists = True
            try:
                self._s3_put(cr, uid, attach.store_fname, content_type=attach.mimetype)
            except S3Error:
                s3_exists = False
            self.write(cr, SUPERUSER_ID, [id], { 's3_exists': s3_exists }, context=context)
        else:
            _logger.warning("S3 is not enabled, dataloss for attachment [%s] is imminent", id)
        return res

    def _file_read(self, cr, uid, fname, bin_size=False, s3_exists=None):
        full_path = self._full_path(cr, uid, fname)
        if not os.path.exists(full_path) and s3_pool:
            if s3_exists:
                self._s3_get(cr, uid, fname)
            elif s3_exists is False:
                _logger.warning("S3 (%s) lookup prevented '%s'", s3_pool.bucket, fname)
        elif os.path.exists(full_path) and s3_pool and s3_exists is None:
            _logger.warning("S3 (%s) detected missing file '%s'", s3_pool.bucket, fname)
        return super(ir_attachment, self)._file_read(cr, uid, fname, bin_size=bin_size)

    def _file_delete(self, cr, uid, fname):
        if s3_pool:
            # using SQL to include files hidden through unlink or due to record rules
            cr.execute("SELECT COUNT(*) FROM ir_attachment WHERE store_fname = %s", (fname,))
            count = cr.fetchone()[0]
            if not count:
                key = self._s3_key(cr.dbname, fname)
                _logger.info("S3 (%s) delete '%s'", s3_pool.bucket, key)
                _logger.increment("s3.delete", 1)
                try:
                    s3_pool.client.delete_object(Bucket=s3_pool.bucket, Key=key)
                except ClientError as e:
                    if e.response['Error']['Code'] != "NoSuchKey":
                        _logger.warning("S3 (%s) delete '%s'", s3_pool.bucket, key, exc_info=True)
        return super(ir_attachment, self)._file_delete(cr, uid, fname)

    def _s3_key(self, dbname, fname):
        return 'filestore/%s/%s' % (dbname, fname)

    def _s3_get(self, cr, uid, fname):
        key = self._s3_key(cr.dbname, fname)
        _logger.info("S3 (%s) get '%s'", s3_pool.bucket, key)
        _logger.increment("s3.get", 1)

        try:
            r = s3_pool.client.get_object(Bucket=s3_pool.bucket, Key=key)
        except ClientError as e:
            _logger.warning("S3 (%s) get '%s'", s3_pool.bucket, key, exc_info=True)
            if e.response['Error']['Code'] == "NoSuchKey":
                raise S3NoSuchKey
            raise S3Error

        bin_data = r['Body'].read()
        checksum = self._compute_checksum(bin_data)
        value = bin_data.encode('base64')
        super(ir_attachment, self)._file_write(cr, uid, value, checksum)

    def _s3_put(self, cr, uid, fname, content_type='application/octet-stream'):
        value = super(ir_attachment, self)._file_read(cr, uid, fname)
        bin_data = value.decode('base64')

        key = self._s3_key(cr.dbname, fname)
        _logger.info("S3 (%s) put '%s'", s3_pool.bucket, key)
        _logger.increment("s3.put", 1)

        try:
            s3_pool.client.put_object(
                Bucket=s3_pool.bucket,
                Key=key,
                Body=bin_data,
                ContentType=content_type,
                ACL='public-read'
            )
        except ClientError:
            _logger.warning("S3 (%s) put '%s'", s3_pool.bucket, key, exc_info=True)
            raise S3Error

    _columns = {
        's3_exists': fields.boolean(string='Exists in s3 bucket'),
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
    }

    _defaults = {
        's3_exists': None,
    }

    @api.multi
    def action_s3_sync(self):
        for attachment in self:
            exists = False
            try:
                attachment._s3_get(attachment.store_fname)
            except S3NoSuchKey:
                exists = False
            except S3Error:
                raise

            try:
                attachment._s3_put(attachment.store_fname)
                exists = True
            except S3Error:
                raise

            attachment.write({ 's3_exists': exists })
