odoo.define('websocket.Session', function(require) {
    'use strict';

  var core = require('web.core');
  var WebSocket = require('websocket.WebSocket');
  var Session = require('web.Session');

  Session.include({

    setup: function() {
      this._super.apply(this, arguments);
      if (this.ws) this.ws.destroy();
      var uri = this.origin.replace('http://', 'ws://').replace('https://', 'wss://');
      this.ws = new WebSocket(uri);
    },

    ws_call: function(path, params, options) {
      var data = {
        path: path,
        rpc: {
          jsonrpc: "2.0",
          method: "call",
          params: params,
          id: Math.floor(Math.random() * 1000 * 1000 * 1000)
        }
      };

      return this.ws.send(data).then(
        function(result) {
          core.bus.trigger('rpc:result', data, result);
          if (result.error) {
            return $.Deferred().reject("server", result.error);
          }
          return result.result;
        }, function(error) {
          var d = $.Deferred();
          return d.reject.apply(d, ["communication"].concat(_.toArray(arguments)));
        }
      );
    },

    ws_rpc: function(url, params, options) {
      var self = this;
      options = _.clone(options || {});
      var shadow = options.shadow || false;
      options.headers = _.extend({}, options.headers)
      if (odoo.debug) {
        options.headers["X-Debug-Mode"] = $.deparam($.param.querystring()).debug;
      }

      delete options.shadow;
      return self.check_session_id().then(function() {
        if (! shadow) self.trigger('request');
        var d = self.ws_call(url, params, options).then(
          function(result) {
            if (! shadow) self.trigger('response');
            return result;
          },
          function(type, error, textStatus, errorThrown) {
            if (type === "server") {
              if (! shadow) self.trigger('response');
              if (error.code === 100) {
                self.uid = false;
              }
              return $.Deferred().reject(error, $.Event());
            } else {
              if (! shadow) self.trigger('response_failed');
              var nerror = {
                code: -32098,
                message: "SocketError"
              };
              return $.Deferred().reject(nerror, $.Event());
            }
          }
        );
        return d.fail(function() { // Allow deferred user to disable rpc_error call in fail
          d.fail(function(error, event) {
            if (!event.isDefaultPrevented()) {
              self.trigger('error', error, event);
            }
          });
        });
      });
    },

    rpc: function() {
      if (this.ws.enabled()) {
        return this.ws_rpc.apply(this, arguments);
      } else {
        return this._super.apply(this, arguments);
      }
    }
  });

});
