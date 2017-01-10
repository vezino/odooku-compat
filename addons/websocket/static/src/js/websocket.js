odoo.define('websocket.WebSocket', function(require) {
    'use strict';

  var core = require('web.core');

  var _WebSocket = core.Class.extend({

    init: function(uri) {
      this._ws = null;
      this._uri = uri;
      this._id = 0;
      this._requests = {}
      this._onclose = this._onclose.bind(this);
      this._onmessage = this._onmessage.bind(this);
      this._onerror = this._onerror.bind(this);
    },

    enabled: function() {
      return 'WebSocket' in window && window.odoo._ws_enabled;
    },

    _bind: function(ws) {
      ws.addEventListener("close", this._onclose);
      ws.addEventListener("message", this._onmessage);
      ws.addEventListener("error", this._onerror);
    },

    _unbind: function(ws) {
      ws.removeEventListener("close", this._onclose);
      ws.removeEventListener("message", this._onmessage);
      ws.removeEventListener("error", this._onerror);
    },

    _onclose: function(evt) {
      this._unbind(evt.target);
      if (this._ws === evt.target) {
        this._ws = null;
        _.forEach(this._requests, function(d) {
          d.reject();
        });
      }
    },

    _onmessage: function(evt) {
      var message = JSON.parse(evt.data);
      if (message.id) {
        if (this._requests && this._requests.hasOwnProperty(message.id)) {
          this._requests[message.id].resolve(message.payload);
        }
      } else {

      }
    },

    _onerror: function(evt) {
      if (this._ws === evt.target && this._ws.readyState !== WebSocket.OPEN) {
        this._ws = null;
        _.forEach(this._requests, function(d) {
          d.reject();
        });
      }
    },

    _aqcuire_ws: function() {
      var self = this;
      var d = $.Deferred();
      if(!this._ws) {
        this._ws = new WebSocket(this._uri);
        this._bind(this._ws);
      }

      if(this._ws.readyState === WebSocket.CONNECTING) {
        this._ws.addEventListener("open", function(evt) {
          d.resolve(evt.target);
        });
      } else {
        d.resolve(this._ws);
      }

      return d.promise();
    },

    _next_id: function() {
      return ++this._id;
    },

    send: function(data) {
      var id = this._next_id();
      var message = {
        id: id,
        payload: data
      }

      var self = this;
      var d = $.Deferred();
      self._requests[id] = d;
      this._aqcuire_ws().then(function(ws) {
        ws.send(JSON.stringify(message));
      });
      return d;
    },

    destroy: function() {
      if (this._ws) {
        this._ws.close();
        this._unbind(this._ws);
        this._ws = null;
      }
    }
  });



  return _WebSocket;

});
