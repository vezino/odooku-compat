# -*- coding: utf-8 -*-

import openerp
from openerp.osv import orm
from odooku.s3 import pool as s3_pool

from odooku.params import params
CDN_ENABLED = getattr(params, 'CDN_ENABLED', False)


class QWeb(orm.AbstractModel):

    _inherit = 'ir.qweb'

    CDN_TRIGGERS = {
        'link':    'href',
        'script':  'src',
        'img':     'src',
    }

    def render_attribute(self, element, name, value, qwebcontext):
        context = qwebcontext.context or {}
        if CDN_ENABLED and not context.get('rendering_bundle') and s3_pool:
            if name == self.CDN_TRIGGERS.get(element.tag):
                cr, uid, context = [getattr(qwebcontext, attr) for attr in ('cr', 'uid', 'context')]
                if value.startswith('/web/content/'):
                    ira = self.pool['ir.attachment']
                    domain = [('url', '=like', value)]
                    attachment_ids = ira.search(cr, openerp.SUPERUSER_ID, domain, order='name asc', context=context)
                    attachments = ira.browse(cr, openerp.SUPERUSER_ID, attachment_ids, context=context)
                    if attachments:
                        # /dbname/filestore/<attachment>
                        value = s3_pool.get_url(cr.dbname, 'filestore', attachments[0].store_fname)
                else:
                    # /modules/<module>/static
                    value = s3_pool.get_url('modules', value[1:])
        raise Exception("WTF")
        return super(QWeb, self).render_attribute(element, name, value, qwebcontext)
