from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.exceptions import WebSocketError

import odoo
import odoo.http
from odooku.wsgi import WSGIServer
from odooku.request import WebRequestMixin

import time
import gevent
import json
import logging

import werkzeug.wrappers


_logger = logging.getLogger(__name__)


class WebSocketRequest(WebRequestMixin, odoo.http.WebRequest):

    def __init__(self, httprequest):
        super(WebSocketRequest, self).__init__(httprequest)

    def dispatch(self):
        raise NotImplementedError()


class WebSocketRpcRequest(WebSocketRequest):

    _request_type = 'json'

    def __init__(self, httprequest, data):
        super(WebSocketRpcRequest, self).__init__(httprequest)
        self.params = data.get('params', {})
        self.id = data.get('id')
        self.context = self.params.pop('context', dict(self.session.context))

    def dispatch(self):

        try:
            result = self._call_function(**self.params)
        except Exception as exception:
            return self._handle_exception(exception)
        return self._json_response(result)

    def _json_response(self, result=None, error=None):
        response = {
            'jsonrpc': '2.0',
            'id': self.id
        }

        if error is not None:
            response['error'] = error
        if result is not None:
            response['result'] = result

        return response

    def _handle_exception(self, exception):
        """Called within an except block to allow converting exceptions
           to arbitrary responses. Anything returned (except None) will
           be used as response."""
        try:
            return super(WebSocketRpcRequest, self)._handle_exception(exception)
        except Exception:
            if not isinstance(exception, (odoo.exceptions.Warning, odoo.http.SessionExpiredException, odoo.exceptions.except_orm)):
                _logger.exception("Exception during JSON request handling.")
            error = {
                    'code': 200,
                    'message': "Odoo Server Error",
                    'data': odoo.http.serialize_exception(exception)
            }
            if isinstance(exception, odoo.http.AuthenticationError):
                error['code'] = 100
                error['message'] = "Odoo Session Invalid"
            if isinstance(exception, odoo.http.SessionExpiredException):
                error['code'] = 100
                error['message'] = "Odoo Session Expired"
            return self._json_response(error=error)


class WebSocketChannel(object):

    def __init__(self):
        self._wss = {}

    def _add(self, ws):
        self._wss[ws] = {}

    def _remove(self, ws):
        del self._wss[ws]

    def get_request(self, httprequest, payload):
        if 'path' in payload:
            httprequest.environ['PATH_INFO'] = payload.get('path')
        if 'rpc' in payload:
            return WebSocketRpcRequest(httprequest, payload.get('rpc'))

    def run_forever(self, ping_delay):
        while True:
            for ws, state in dict(self._wss).iteritems():
                if ws.closed:
                    self._remove(ws)
                    continue

                # Keep socket alive on Heroku (or other platforms).
                last_ping = state.get('last_ping', None)
                now = int(round(time.time()))
                if not last_ping or last_ping + ping_delay < now:
                    state['last_ping'] = now
                    try:
                        ws.send(json.dumps({'ping': now}))
                    except WebSocketError:
                        self._remove(ws)
                        continue

            gevent.sleep(1)

    def dispatch(self, request):
        with odoo.api.Environment.manage():
            with request:
                try:
                    odoo.registry(request.session.db).check_signaling()
                    with odoo.tools.mute_logger('odoo.sql_db'):
                        ir_http = request.registry['ir.http']
                except (AttributeError, psycopg2.OperationalError, psycopg2.ProgrammingError):
                    result = {}
                else:
                    result = ir_http._dispatch()
                    ir_http.pool.signal_caches_change()

        return result

    def respond(self, ws, httprequest, message):
        if any(key not in message for key in ['id', 'payload']):
            # Invalid message, close connection and abort
            ws.close()
            return

        response = {
            'id': message.get('id'),
        }

        request = self.get_request(httprequest, message.get('payload'))
        if request:
            payload = self.dispatch(request)
            response.update({
                'payload': payload
            })
        else:
            response.update({
                'error': {
                    'message': "Unknown payload"
                }
            })

        try:
            ws.send(json.dumps(response))
        except WebSocketError:
            pass

    def listen(self, ws, environ):
        self._add(ws)
        while not ws.closed:
            try:
                message = ws.receive()
            except WebSocketError:
                break

            if message is not None:
                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    break

                # Odoo heavily relies on httprequests, for each message
                # a new httprequest will be created. This request will be
                # based on the original environ from the socket initialization
                # request.
                httprequest = werkzeug.wrappers.Request(environ.copy())
                explicit_session = odoo.http.root.setup_session(httprequest)
                odoo.http.root.setup_db(httprequest)
                odoo.http.root.setup_lang(httprequest)
                gevent.spawn(self.respond, ws, httprequest, message)

        self._remove(ws)


class WebSocketServer(WSGIServer):

    def __init__(self, *args, **kwargs):
        kwargs['handler_class'] = WebSocketHandler
        super(WebSocketServer, self).__init__(*args, **kwargs)

    def load(self, *args, **kwargs):
        application = super(WebSocketServer, self).load(*args, **kwargs)
        _logger.info("Websockets enabled")
        return WebSocketApplicationWrapper(application, self.timeout)


class WebSocketApplicationWrapper(object):

    def __init__(self, application, ping_delay=None):
        self._application = application
        self._channel = WebSocketChannel()
        gevent.spawn(self._channel.run_forever, ping_delay)

    def __call__(self, environ, start_response):
        ws = environ.get('wsgi.websocket')
        if ws:
            self._channel.listen(ws, environ.copy())
            return []
        else:
            return self._application(environ, start_response)
