# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import logging.handlers
import os
import platform
import pprint
import release
import sys
import threading

import psycopg2

import openerp
import sql_db
import tools

_logger = logging.getLogger(__name__)

def log(logger, level, prefix, msg, depth=None):
    indent=''
    indent_after=' '*len(prefix)
    for line in (prefix + pprint.pformat(msg, depth=depth)).split('\n'):
        logger.log(level, indent+line)
        indent=indent_after

def LocalService(name):
    """
    The openerp.netsvc.LocalService() function is deprecated. It still works
    in two cases: workflows and reports. For workflows, instead of using
    LocalService('workflow'), openerp.workflow should be used (better yet,
    methods on openerp.osv.orm.Model should be used). For reports,
    openerp.report.render_report() should be used (methods on the Model should
    be provided too in the future).
    """
    assert openerp.conf.deprecation.allow_local_service
    _logger.warning("LocalService() is deprecated since march 2013 (it was called with '%s')." % name)

    if name == 'workflow':
        return openerp.workflow

    if name.startswith('report.'):
        report = openerp.report.interface.report_int._reports.get(name)
        if report:
            return report
        else:
            dbname = getattr(threading.currentThread(), 'dbname', None)
            if dbname:
                registry = openerp.modules.registry.RegistryManager.get(dbname)
                with registry.cursor() as cr:
                    return registry['ir.actions.report.xml']._lookup_report(cr, name[len('report.'):])


# PATCH !!
def init_logger():
    pass
