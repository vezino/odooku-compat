# -*- coding: utf-8 -*-

import ast

import odoo
from odoo import models, SUPERUSER_ID

from odooku.s3 import pool as s3_pool
from odooku.params import params

CDN_ENABLED = getattr(params, 'CDN_ENABLED', False)


class QWeb(models.AbstractModel):

    _inherit = 'ir.qweb'

    CDN_TRIGGERS = {
        'link':    'href',
        'script':  'src',
        'img':     'src',
    }

    def _website_build_attribute(self, tagName, name, value, options, values):
        if CDN_ENABLED and s3_pool:
            if name == self.CDN_TRIGGERS.get(element.tag):
                parts = value.split('/')
                cr, context = [getattr(options, attr) for attr in ('cr', 'context')]
                if value.startswith('/web/content/'):
                    ira = self.pool['ir.attachment']
                    domain = [('url', '=like', value)]
                    attachment_ids = ira.search(cr, SUPERUSER_ID, domain, order='name asc', context=context)
                    attachments = ira.browse(cr, SUPERUSER_ID, attachment_ids, context=context)
                    if attachments:
                        # /filestore/<dbname/<attachment>
                        value = s3_pool.get_url('filestore', cr.dbname, attachments[0].store_fname)
                elif len(parts) > 2 and parts[1] == 'static':
                    # /modules/<module>/static
                    value = s3_pool.get_url('modules', value[1:])

        return value

    def _wrap_build_attributes(self, el, items, options):
        """ Map items corresponding to URL and CDN attributes to an ast expression. """
        if options.get('rendering_bundle'):
            return items

        cdn_att = self.CDN_TRIGGERS.get(el.tag)

        def process(item):
            if isinstance(item, tuple) and (item[0] in (cdn_att,)):
                return (item[0], ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_website_build_attribute',
                        ctx=ast.Load()
                    ),
                    args=[
                        ast.Str(el.tag),
                        ast.Str(item[0]),
                        item[1],
                        ast.Name(id='options', ctx=ast.Load()),
                        ast.Name(id='values', ctx=ast.Load()),
                    ], keywords=[],
                    starargs=None, kwargs=None
                ))
            else:
                return item

        return map(process, items)

    def _compile_static_attributes(self, el, options):
        items = super(QWeb, self)._compile_static_attributes(el, options)
        return self._wrap_build_attributes(el, items, options)

    def _compile_dynamic_attributes(self, el, options):
        items = super(QWeb, self)._compile_dynamic_attributes(el, options)
        return self._wrap_build_attributes(el, items, options)

    # method called by computing code

    def _get_dynamic_att(self, tagName, atts, options, values):
        atts = super(QWeb, self)._get_dynamic_att(tagName, atts, options, values)
        if options.get('rendering_bundle'):
            return atts
        for name, value in atts.iteritems():
            atts[name] = self._website_build_attribute(tagName, name, value, options, values)
        return atts

    def _is_static_node(self, el):
        cdn_att = self.CDN_TRIGGERS.get(el.tag)
        return super(QWeb, self)._is_static_node(el) and \
                (not cdn_att or not el.get(cdn_att))
