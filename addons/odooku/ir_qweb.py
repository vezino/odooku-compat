# -*- coding: utf-8 -*-

from openerp.osv import orm
from openerp.tools import config


class QWeb(orm.AbstractModel):

    _inherit = 'ir.qweb'

    def render_tag_call_assets(self, element, template_attributes, generated_attributes, qwebcontext):
        qwebcontext = qwebcontext.copy()
        if config['test_enable']:
            # Dirty hack to make phantomjs tests work. Seems AssetsBundle's
            # are not commited once phantomjs tests are run.
            qwebcontext.context = dict(
                qwebcontext.context, commit_assetsbundle=True
            )

        return super(QWeb, self).render_tag_call_assets(element, template_attributes, generated_attributes, qwebcontext)
