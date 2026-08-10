"""Local web server for the MT5 mobile-style panel.

Runs on your own PC, talks to the MetaTrader 5 terminal that is already open,
and serves a phone-like interface at http://127.0.0.1:8777.

    pip install MetaTrader5
    python server.py

Nothing leaves the machine: the socket is bound to the loopback interface and
every API call must carry a key that is generated fresh on each start.

    python server.py --demo     interface with fake prices, no MT5 needed
    python server.py --port 9000
    python server.py --open     launch the browser automatically
"""

import argparse
import json
import mimetypes
import os
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")
CONFIG_PATH = os.path.join(HERE, "config.json")

bridge = None          # set in main(): mt5_bridge or demo_bridge
API_KEY = ""
READ_ONLY = False
_trade_lock = threading.Lock()


class ApiError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# request helpers
# --------------------------------------------------------------------------

def _num(params, name, default=None, required=False):
    raw = params.get(name, default)
    if raw in (None, ""):
        if required:
            raise ApiError("Missing field: %s" % name)
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise ApiError("Field %s must be a number" % name)


def _str(params, name, default="", required=False):
    raw = params.get(name, default)
    if raw in (None, "") and required:
        raise ApiError("Missing field: %s" % name)
    return str(raw or default)


# --------------------------------------------------------------------------
# API routes
# --------------------------------------------------------------------------

def api_status(p):
    return bridge.status()


def api_account(p):
    return bridge.account()


def api_symbols(p):
    watch = _str(p, "all", "0") not in ("1", "true", "yes")
    return {"symbols": bridge.symbols(watch_only=watch, search=_str(p, "q"))}


def api_symbol(p):
    return bridge.symbol_info(_str(p, "symbol", required=True))


def api_candles(p):
    return {"candles": bridge.candles(_str(p, "symbol", required=True),
                                      _str(p, "tf", "M15"),
                                      int(_num(p, "count", 180)))}


def api_snapshot(p):
    """Everything the main screen needs, in one round trip."""
    watch = bridge.symbols(watch_only=True)
    return {
        "account": bridge.account(),
        "positions": bridge.positions(),
        "orders": bridge.pending_orders(),
        "symbols": watch,
        "demo": getattr(bridge, "DEMO", False),
    }


def api_history(p):
    return bridge.history(days=int(_num(p, "days", 30)))


def api_select(p):
    _guard_trading()
    return bridge.select_symbol(_str(p, "symbol", required=True),
                                _str(p, "enable", "1") in ("1", "true", "yes"))


def api_order(p):
    _guard_trading()
    with _trade_lock:
        return bridge.market_order(
            symbol=_str(p, "symbol", required=True),
            side=_str(p, "side", required=True),
            volume=_num(p, "volume", required=True),
            sl=_num(p, "sl"),
            tp=_num(p, "tp"),
            deviation=int(_num(p, "deviation", 20)),
        )


def api_pending(p):
    _guard_trading()
    with _trade_lock:
        return bridge.pending_order(
            symbol=_str(p, "symbol", required=True),
            order_type=_str(p, "type", required=True),
            volume=_num(p, "volume", required=True),
            price=_num(p, "price", required=True),
            sl=_num(p, "sl"),
            tp=_num(p, "tp"),
        )


def api_modify(p):
    _guard_trading()
    with _trade_lock:
        return bridge.modify_position(int(_num(p, "ticket", required=True)),
                                      sl=_num(p, "sl"), tp=_num(p, "tp"))


def api_close(p):
    _guard_trading()
    with _trade_lock:
        return bridge.close_position(int(_num(p, "ticket", required=True)),
                                     volume=_num(p, "volume"))


def api_close_all(p):
    _guard_trading()
    with _trade_lock:
        return bridge.close_all(symbol=_str(p, "symbol") or None)


def api_cancel(p):
    _guard_trading()
    with _trade_lock:
        return bridge.cancel_order(int(_num(p, "ticket", required=True)))


def api_calc_lot(p):
    return bridge.calc_lot(_str(p, "symbol", required=True),
                           _num(p, "risk", required=True),
                           _num(p, "sl_points", required=True))


def _guard_trading():
    if READ_ONLY:
        raise ApiError("Panel is running in read-only mode "
                       "(started with --read-only).", 403)


GET_ROUTES = {
    "/api/status": api_status,
    "/api/account": api_account,
    "/api/symbols": api_symbols,
    "/api/symbol": api_symbol,
    "/api/candles": api_candles,
    "/api/snapshot": api_snapshot,
    "/api/history": api_history,
    "/api/calc_lot": api_calc_lot,
}

POST_ROUTES = {
    "/api/order": api_order,
    "/api/pending": api_pending,
    "/api/modify": api_modify,
    "/api/close": api_close,
    "/api/close_all": api_close_all,
    "/api/cancel": api_cancel,
    "/api/select": api_select,
    "/api/calc_lot": api_calc_lot,
}


# --------------------------------------------------------------------------
# HTTP layer
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "mt5panel"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep the console readable
        pass

    # -- plumbing ---------------------------------------------------------
    def _send(self, code, body, ctype="application/json; charset=utf-8",
              extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, payload):
        self._send(code, json.dumps(payload, default=str))

    def _local_only(self):
        """Reject anything that did not come from this machine's browser."""
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "[::1]", "::1"):
            return False
        origin = self.headers.get("Origin")
        if origin:
            netloc = urlparse(origin).hostname
            if netloc not in ("127.0.0.1", "localhost", "::1"):
                return False
        return True

    def _authorised(self, query):
        key = self.headers.get("X-Panel-Key") or (query.get("k", [""])[0])
        return secrets.compare_digest(key or "", API_KEY)

    # -- routing ----------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path.startswith("/api/"):
            return self._handle_api(url.path, query, GET_ROUTES,
                                    {k: v[0] for k, v in query.items()})
        return self._serve_static(url.path)

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if not url.path.startswith("/api/"):
            return self._json(404, {"error": "Not found"})
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            params = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(params, dict):
                raise ValueError
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "Body must be a JSON object"})
        return self._handle_api(url.path, query, POST_ROUTES, params)

    def _handle_api(self, path, query, routes, params):
        if not self._local_only():
            return self._json(403, {"error": "Only reachable from this PC"})
        if not self._authorised(query):
            return self._json(401, {"error": "Bad or missing panel key"})
        handler = routes.get(path)
        if handler is None:
            return self._json(404, {"error": "Unknown endpoint: %s" % path})
        try:
            return self._json(200, {"ok": True, "data": handler(params)})
        except ApiError as exc:
            return self._json(exc.code, {"ok": False, "error": str(exc)})
        except Exception as exc:  # bridge failures land here
            return self._json(400, {"ok": False, "error": str(exc)})

    # -- static files -----------------------------------------------------
    def _serve_static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = os.path.normpath(os.path.join(WEB_DIR, rel))
        if not target.startswith(WEB_DIR) or not os.path.isfile(target):
            return self._send(404, "Not found", "text/plain; charset=utf-8")
        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        with open(target, "rb") as fh:
            body = fh.read()
        if rel == "index.html":
            body = body.replace(b"__PANEL_KEY__", API_KEY.encode())
        self._send(200, body, ctype)


# --------------------------------------------------------------------------

def load_config():
    if not os.path.isfile(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError) as exc:
        print("! config.json ignored (%s)" % exc)
        return {}


def main(argv=None):
    global bridge, API_KEY, READ_ONLY

    ap = argparse.ArgumentParser(description="MT5 mobile-style panel")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--demo", action="store_true",
                    help="fake prices, no MT5 terminal required")
    ap.add_argument("--read-only", action="store_true",
                    help="disable every order/close/modify endpoint")
    ap.add_argument("--open", action="store_true",
                    help="open the panel in the default browser")
    ap.add_argument("--terminal", default=None,
                    help="path to terminal64.exe if it is not auto-detected")
    args = ap.parse_args(argv)

    cfg = load_config()
    READ_ONLY = args.read_only or bool(cfg.get("read_only"))
    API_KEY = secrets.token_urlsafe(24)

    if args.demo:
        import demo_bridge
        bridge = demo_bridge
    else:
        import mt5_bridge
        bridge = mt5_bridge

    print("MT5 Panel")
    print("  mode      : %s%s" % ("demo (offline)" if args.demo else "live terminal",
                                  " · read-only" if READ_ONLY else ""))
    try:
        bridge.start(terminal_path=args.terminal or cfg.get("terminal_path"),
                     login=cfg.get("login"), password=cfg.get("password"),
                     server=cfg.get("server"))
        acc = bridge.account()
        print("  account   : %s (%s) %s %.2f"
              % (acc["login"], acc["server"], acc["currency"], acc["balance"]))
    except Exception as exc:
        print("  connection: FAILED - %s" % exc)
        print("  Open MetaTrader 5, log in, then start this script again.")
        if not args.demo:
            print("  Tip: run `python server.py --demo` to preview the panel.")
            return 1

    url = "http://127.0.0.1:%d/?k=%s" % (args.port, API_KEY)
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    httpd.daemon_threads = True
    print("  open this : %s" % url)
    print("  (Ctrl+C to stop)")
    if args.open:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        httpd.server_close()
        bridge.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
