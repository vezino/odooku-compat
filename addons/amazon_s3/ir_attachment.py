# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, SUPERUSER_ID
from openerp.osv import fields, osv

import os
import logging
import boto3


_logger = logging.getLogger(__name__)


S3_BUCKET = 'S3_BUCKET'
AWS_ACCESS_KEY_ID= 'AWS_ACCESS_KEY_ID'
AWS_SECRET_ACCESS_KEY = 'AWS_SECRET_ACCESS_KEY'


class S3NotExistsError(Exception):
    pass


class ir_attachment(osv.osv):

    _inherit = 'ir.attachment'

    @property
    def _s3_enabled(self):
        return all(
            (key in os.environ)
            for key in
            (S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        )

    @property
    def _s3_bucket(self):
        return os.environ.get(S3_BUCKET)

    __s3_client = None

    @property
    def _s3_client(self):
        if self.__s3_client is None:
            self.__s3_client = boto3.client(
                's3',
                aws_access_key_id=os.environ.get(AWS_ACCESS_KEY_ID),
                aws_secret_access_key=os.environ.get(AWS_SECRET_ACCESS_KEY)
            )

        return self.__s3_client

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        result = {}
        bin_size = context.get('bin_size')
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.store_fname:
                try:
                    result[attach.id] = self._file_read(cr, uid, attach.store_fname, bin_size, attach.s3_exists)
                except S3NotExistsError:
                    # SUPERUSER_ID as probably don't have write access, trigger during create
                    self.write(cr, SUPERUSER_ID, [attach.id], { 's3_exists': False }, context=context)
                    result[attach.id] = ''
            else:
                result[attach.id] = attach.db_datas
        return result

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        res = super(ir_attachment, self)._data_set(cr, uid, id, name, value, arg, context=None)
        self.write(cr, SUPERUSER_ID, [id], { 's3_exists': True }, context=context)
        return res

    def _file_read(self, cr, uid, fname, bin_size=False, s3_exists=True):
        full_path = self._full_path(cr, uid, fname)
        if not os.path.exists(full_path) and s3_exists and self._s3_enabled:
            self._s3_get(cr, uid, fname)
        return super(ir_attachment, self)._file_read(cr, uid, fname, bin_size=bin_size)

    def _file_write(self, cr, uid, value, checksum):
        res = super(ir_attachment, self)._file_write(cr, uid, value, checksum)
        if self._s3_enabled:
            self._s3_put(cr, uid, self.store_fname)
        return res

    def _file_delete(self, cr, uid, fname):
        if self._s3_enabled:
            try:
                self._s3_client.delete_object(Bucket=self._s3_bucket, Key=fname)
            except Exception:
                pass

        return super(ir_attachment, self)._file_delete(cr, uid, fname)

    def _s3_get(self, cr, uid, fname):
        try:
            _logger.info("Retrieving s3 object %s", fname)
            r = self._s3_client.get_object(Bucket=self._s3_bucket, Key=fname)
        except Exception:
            _logger.info("_s3_get %s", fname, exc_info=True)
            raise S3NotExistsError(fname)

        bin_data = r['Body'].read()
        checksum = self._compute_checksum(bin_data)
        super(ir_attachment, self)._file_write(cr, uid, bin_data, checksum)
        _logger.info("_s3_get %s (%s)", fname, checksum, exc_info=True)

    def _s3_put(self, cr, uid, fname):
        bin_data = super(ir_attachment, self)._file_read(cr, uid, fname)
        self._s3_client.put_object(Bucket=self._s3_bucket, Key=fname, Body=bin_data)
        _logger.info("_s3_put %s", fname)

    _columns = {
        's3_exists': fields.boolean(string='Exists in s3 bucket'),
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
    }

    _defaults = {
        's3_exists': True,
    }

    @api.multi
    def action_s3_sync(self):
        for attachment in self:
            exists = attachment.s3_exists
            if exists:
                try:
                    attachment._s3_get(attachment.store_fname)
                    continue
                except S3NotExistsError:
                    exists = False

            try:
                attachment._s3_put(attachment.store_fname)
                exists = True
            except Exception:
                pass

            attachment.write({ 's3_exists': exists })
