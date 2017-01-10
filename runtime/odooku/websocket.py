from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.exceptions import WebSocketError

import odoo
import odoo.http
from odooku.wsgi import WSGIServer

import gevent
import json
import logging

import werkzeug.wrappers


_logger = logging.getLogger(__name__)


class WebSocketRequest(odoo.http.WebRequest):

    _request_type = 'json'

    def __init__(self, httprequest, payload):
        path = payload['path']
        httprequest.environ['PATH_INFO'] = path
        super(WebSocketRequest, self).__init__(httprequest)
        rpc = payload.get('rpc')
        self.params = rpc.get('params', {})
        self.id = rpc.get('id')
        self.context = self.params.pop('context', dict(self.session.context))

    def dispatch(self):
        result = {
            'jsonrpc': '2.0',
            'id': self.id,
            'result': self._call_function(**self.params)
        }

        return result


class WebSocketChannel(object):

    def __init__(self, ws, environ):
        self.ws = ws
        self.environ = environ

    def dispatch(self, httprequest, message):
        message = json.loads(message)
        request = WebSocketRequest(httprequest, message.get('payload'))
        with odoo.api.Environment.manage():
            with request:
                db = request.session.db
                try:
                    odoo.registry(db).check_signaling()
                    with odoo.tools.mute_logger('odoo.sql_db'):
                        ir_http = request.registry['ir.http']
                except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError):
                    pass
                else:
                    result = ir_http._dispatch()
                    ir_http.pool.signal_caches_change()

        response = {
            'id': message.get('id'),
            'payload': result
        }

        response = json.dumps(response)

        try:
            self.ws.send(response)
        except WebSocketError:
            pass

    def loop_forever(self):
        while not self.ws.closed:
            try:
                message = self.ws.receive()
            except WebSocketError:
                break

            if message is not None:
                httprequest = werkzeug.wrappers.Request(self.environ.copy())
                explicit_session = odoo.http.root.setup_session(httprequest)
                odoo.http.root.setup_db(httprequest)
                odoo.http.root.setup_lang(httprequest)
                gevent.spawn(self.dispatch, httprequest, message)


class WebSocketServer(WSGIServer):

    def __init__(self, *args, **kwargs):
        kwargs['handler_class'] = WebSocketHandler
        super(WebSocketServer, self).__init__(*args, **kwargs)

    def load(self, *args, **kwargs):
        application = super(WebSocketServer, self).load(*args, **kwargs)
        _logger.info("Websockets enabled")
        return WebSocketApplicationWrapper(application)


class WebSocketApplicationWrapper(object):

    def __init__(self, application):
        self._application = application

    def __call__(self, environ, start_response):
        ws = environ.get('wsgi.websocket')
        if ws:
            channel = WebSocketChannel(ws, environ)
            channel.loop_forever()
            return []
        else:
            return self._application(environ, start_response)
