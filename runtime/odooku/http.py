import contextlib

import openerp.http
import openerp.service.db
from openerp.tools import config
from openerp.tools.func import lazy_property

import werkzeug.datastructures
from werkzeug.contrib.sessions import FilesystemSessionStore


from odooku.redis import pool as redis_pool
from odooku.session import RedisSessionStore

import logging

_logger = logging.getLogger(__name__)



IGNORE_EXCEPTIONS = (
    openerp.osv.orm.except_orm,
    openerp.exceptions.AccessError,
    openerp.exceptions.ValidationError,
    openerp.exceptions.MissingError,
    openerp.exceptions.AccessDenied,
    openerp.exceptions.Warning,
    openerp.exceptions.RedirectWarning,
    werkzeug.exceptions.HTTPException
)


class WebRequestMixin(object):

    def _handle_exception(self, exception):
        if not isinstance(exception, IGNORE_EXCEPTIONS):
            _logger.exception("Exception caught", exc_info=True)
        return super(WebRequestMixin, self)._handle_exception(exception)


class HttpRequest(WebRequestMixin, openerp.http.HttpRequest):
    pass


class JsonRequest(WebRequestMixin, openerp.http.JsonRequest):
    pass


class Root(openerp.http.Root):

    @lazy_property
    def session_store(self):
        if redis_pool:
            _logger.info("HTTP Sessions stored in redis")
            return RedisSessionStore(session_class=OpenERPSession)
        else:
            path = config.session_dir
            _logger.info("HTTP sessions stored locally in: %s", path)
            return FilesystemSessionStore(path, session_class=OpenERPSession)

    def setup_db(self, httprequest):
        db = httprequest.session.db
        if db and db not in openerp.service.db.list_dbs(True):
            _logger.warn("Logged into database '%s', but db list "
                         "rejects it; logging session out.", db)
            httprequest.session.logout()
            httprequest.session.db = None
        super(Root, self).setup_db(httprequest)

    def setup_session(self, httprequest):
        if isinstance(self.session_store, RedisSessionStore):
            sid = httprequest.args.get('session_id')
            explicit_session = True
            if not sid:
                sid =  httprequest.headers.get("X-Openerp-Session-Id")
            if not sid:
                sid = httprequest.cookies.get('session_id')
                explicit_session = False
            if sid is None:
                httprequest.session = self.session_store.new()
            else:
                httprequest.session = self.session_store.get(sid)
            return explicit_session
        else:
            return super(Root, self).setup_session(httprequest)

    def preload(self):
        self._loaded = True
        self.load_addons()

    def get_request(self, httprequest):
        # deduce type of request
        if httprequest.args.get('jsonp'):
            return JsonRequest(httprequest)
        if httprequest.mimetype in ("application/json", "application/json-rpc"):
            return JsonRequest(httprequest)
        else:
            return HttpRequest(httprequest)


class OpenERPSession(openerp.http.OpenERPSession):

    def save_request_data(self):
        root = openerp.http.root
        if isinstance(root.session_store, RedisSessionStore):
            req = request.httprequest
            if req.files:
                raise NotImplementedError("Cannot save request data with files")

            self['serialized_request_data'] = {
                'form': req.form
            }
        else:
            super(OpenERPSession, self).save_request_data()

    @contextlib.contextmanager
    def load_request_data(self):
        root = openerp.http.root
        if isinstance(root.session_store, RedisSessionStore):
            data = self.pop('serialized_request_data', None)
            if data:
                yield werkzeug.datastructures.CombinedMultiDict([data['form']])
            else:
                yield None
        else:
            with super(OpenERPSession, self).load_request_data() as data:
                yield data
