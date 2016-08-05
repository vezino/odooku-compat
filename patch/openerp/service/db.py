# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE_ODOO file for full copyright and licensing details.

import json
import logging
import os
import shutil
import tempfile
import threading
import traceback
import xml.etree.ElementTree as ET
import zipfile

from functools import wraps
from contextlib import closing

import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
import openerp.release
import openerp.sql_db
import openerp.tools

_logger = logging.getLogger(__name__)

class DatabaseExists(Warning):
    pass

#----------------------------------------------------------
# Master password required
#----------------------------------------------------------

def check_super(passwd):
    if passwd and passwd == openerp.tools.config['admin_passwd']:
        return True
    raise openerp.exceptions.AccessDenied()

# This should be moved to openerp.modules.db, along side initialize().
def _initialize_db(id, db_name, demo, lang, user_password, login='admin', country_code=None):
    try:
        db = openerp.sql_db.db_connect(db_name)
        with closing(db.cursor()) as cr:
            # TODO this should be removed as it is done by RegistryManager.new().
            openerp.modules.db.initialize(cr)
            openerp.tools.config['lang'] = lang
            cr.commit()

        registry = openerp.modules.registry.RegistryManager.new(
            db_name, demo, None, update_module=True)

        with closing(db.cursor()) as cr:
            if lang:
                modobj = registry['ir.module.module']
                mids = modobj.search(cr, SUPERUSER_ID, [('state', '=', 'installed')])
                modobj.update_translations(cr, SUPERUSER_ID, mids, lang)

            if country_code:
                countries = registry['res.country'].search_read(cr, SUPERUSER_ID, [('code', 'ilike', country_code)], fields=['id'])
                if countries:
                    registry['res.company'].write(cr, SUPERUSER_ID, 1, {'country_id': countries[0]['id']})

            # update admin's password and lang and login
            values = {'password': user_password, 'lang': lang}
            if login:
                values['login'] = login
                emails = openerp.tools.email_split(login)
                if emails:
                    values['email'] = emails[0]
            registry['res.users'].write(cr, SUPERUSER_ID, [SUPERUSER_ID], values)

            cr.execute('SELECT login, password FROM res_users ORDER BY login')
            cr.commit()
    except Exception, e:
        _logger.exception('CREATE DATABASE failed:')

def _create_empty_database(name):
    # We can't
    pass

def exp_create_database(db_name, demo, lang, user_password='admin', login='admin', country_code=None):
    """ Similar to exp_create but blocking."""
    _logger.info('Create database `%s`.', db_name)
    _create_empty_database(db_name)
    _initialize_db(id, db_name, demo, lang, user_password, login, country_code)
    return True

def exp_duplicate_database(db_original_name, db_name):
    # We can't
    return False

def _drop_conn(cr, db_name):
    # Try to terminate all other connections that might prevent
    # dropping the database
    try:
        # PostgreSQL 9.2 renamed pg_stat_activity.procpid to pid:
        # http://www.postgresql.org/docs/9.2/static/release-9-2.html#AEN110389
        pid_col = 'pid' if cr._cnx.server_version >= 90200 else 'procpid'

        cr.execute("""SELECT pg_terminate_backend(%(pid_col)s)
                      FROM pg_stat_activity
                      WHERE datname = %%s AND
                            %(pid_col)s != pg_backend_pid()""" % {'pid_col': pid_col},
                   (db_name,))
    except Exception:
        pass

def exp_drop(db_name):
    # We can't
    return False

def exp_dump(db_name, format):
    with tempfile.TemporaryFile() as t:
        dump_db(db_name, t, format)
        t.seek(0)
        return t.read().encode('base64')

def dump_db_manifest(cr):
    pg_version = "%d.%d" % divmod(cr._obj.connection.server_version / 100, 100)
    cr.execute("SELECT name, latest_version FROM ir_module_module WHERE state = 'installed'")
    modules = dict(cr.fetchall())
    manifest = {
        'odoo_dump': '1',
        'db_name': cr.dbname,
        'version': openerp.release.version,
        'version_info': openerp.release.version_info,
        'major_version': openerp.release.major_version,
        'pg_version': pg_version,
        'modules': modules,
    }
    return manifest

def dump_db(db_name, stream, backup_format='zip'):
    """Dump database `db` into file-like object `stream` if stream is None
    return a file object with the dump """

    _logger.info('DUMP DB: %s format %s', db_name, backup_format)

    cmd = ['pg_dump', '--no-owner']
    cmd.append(db_name)

    if backup_format == 'zip':
        with openerp.tools.osutil.tempdir() as dump_dir:
            filestore = openerp.tools.config.filestore(db_name)
            if os.path.exists(filestore):
                shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))
            with open(os.path.join(dump_dir, 'manifest.json'), 'w') as fh:
                db = openerp.sql_db.db_connect(db_name)
                with db.cursor() as cr:
                    json.dump(dump_db_manifest(cr), fh, indent=4)
            cmd.insert(-1, '--file=' + os.path.join(dump_dir, 'dump.sql'))
            openerp.tools.exec_pg_command(*cmd)
            if stream:
                openerp.tools.osutil.zip_dir(dump_dir, stream, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
            else:
                t=tempfile.TemporaryFile()
                openerp.tools.osutil.zip_dir(dump_dir, t, include_dir=False, fnct_sort=lambda file_name: file_name != 'dump.sql')
                t.seek(0)
                return t
    else:
        cmd.insert(-1, '--format=c')
        stdin, stdout = openerp.tools.exec_pg_command_pipe(*cmd)
        if stream:
            shutil.copyfileobj(stdout, stream)
        else:
            return stdout

def exp_restore(db_name, data, copy=False):
    data_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        data_file.write(data.decode('base64'))
        data_file.close()
        restore_db(db_name, data_file.name, copy=copy)
    finally:
        os.unlink(data_file.name)
    return True

def restore_db(db, dump_file, copy=False):
    assert isinstance(db, basestring)
    filestore_path = None
    with openerp.tools.osutil.tempdir() as dump_dir:
        if zipfile.is_zipfile(dump_file):
            # v8 format
            with zipfile.ZipFile(dump_file, 'r') as z:
                # only extract known members!
                filestore = [m for m in z.namelist() if m.startswith('filestore/')]
                z.extractall(dump_dir, ['dump.sql'] + filestore)

                if filestore:
                    filestore_path = os.path.join(dump_dir, 'filestore')

            pg_cmd = 'psql'
            pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

        else:
            # <= 7.0 format (raw pg_dump output)
            pg_cmd = 'pg_restore'
            pg_args = ['--no-owner', dump_file]

        args = []
        args.append('--dbname=' + db)
        pg_args = args + pg_args

        if openerp.tools.exec_pg_command(pg_cmd, *pg_args):
            raise Exception("Couldn't restore database")

        registry = openerp.modules.registry.RegistryManager.new(db)
        with registry.cursor() as cr:
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                registry['ir.config_parameter'].init(cr, force=True)
            if filestore_path:
                filestore_dest = registry['ir.attachment']._filestore(cr, SUPERUSER_ID)
                shutil.move(filestore_path, filestore_dest)

            if openerp.tools.config['unaccent']:
                try:
                    with cr.savepoint():
                        cr.execute("CREATE EXTENSION unaccent")
                except psycopg2.Error:
                    pass

    _logger.info('RESTORE DB: %s', db)

def exp_rename(old_name, new_name):
    # We can't
    return False

def exp_change_admin_password(new_password):
    openerp.tools.config['admin_passwd'] = new_password
    openerp.tools.config.save()
    return True

def exp_migrate_databases(databases):
    for db in databases:
        _logger.info('migrate database %s', db)
        openerp.tools.config['update']['base'] = True
        openerp.modules.registry.RegistryManager.new(db, force_demo=False, update_module=True)
    return True

#----------------------------------------------------------
# No master password required
#----------------------------------------------------------

@openerp.tools.mute_logger('openerp.sql_db')
def exp_db_exist(db_name):
    ## Not True: in fact, check if connection to database is possible. The database may exists
    return bool(openerp.sql_db.db_connect(db_name))

def list_dbs(force=False):
    if not openerp.tools.config['list_db'] and not force:
        raise openerp.exceptions.AccessDenied()
    return openerp.tools.config.get('db_name', '').split(',')

def exp_list(document=False):
    if not openerp.tools.config['list_db']:
        raise openerp.exceptions.AccessDenied()
    return list_dbs()

def exp_list_lang():
    return openerp.tools.scan_languages()

def exp_list_countries():
    list_countries = []
    root = ET.parse(os.path.join(openerp.tools.config['root_path'], 'addons/base/res/res_country_data.xml')).getroot()
    for country in root.find('data').findall('record[@model="res.country"]'):
        name = country.find('field[@name="name"]').text
        code = country.find('field[@name="code"]').text
        list_countries.append([code, name])
    return sorted(list_countries, key=lambda c: c[1])

def exp_server_version():
    """ Return the version of the server
        Used by the client to verify the compatibility with its own version
    """
    return openerp.release.version

#----------------------------------------------------------
# db service dispatch
#----------------------------------------------------------

def dispatch(method, params):
    g = globals()
    exp_method_name = 'exp_' + method
    if method in ['db_exist', 'list', 'list_lang', 'server_version']:
        return g[exp_method_name](*params)
    elif exp_method_name in g:
        passwd = params[0]
        params = params[1:]
        check_super(passwd)
        return g[exp_method_name](*params)
    else:
        raise KeyError("Method not found: %s" % method)
