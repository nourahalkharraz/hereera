"""Offline stand-in for mt5_bridge.

Same function signatures, fake prices and an in-memory account. Used by
`python server.py --demo` so the interface can be explored (or developed on a
non-Windows machine) without a running MT5 terminal. Nothing here touches a
real broker.
"""

import math
import random
import threading
import time

from mt5_bridge import BridgeError  # reuse the same error type

DEMO = True
_lock = threading.Lock()

_SPECS = {
    # symbol: (start price, digits, point, spread points, tick value/lot, description)
    "EURUSD": (1.0865, 5, 0.00001, 12, 1.0, "Euro vs US Dollar"),
    "GBPUSD": (1.2712, 5, 0.00001, 15, 1.0, "Great Britain Pound vs US Dollar"),
    "USDJPY": (151.42, 3, 0.001, 14, 0.66, "US Dollar vs Japanese Yen"),
    "XAUUSD": (2334.50, 2, 0.01, 25, 1.0, "Gold vs US Dollar"),
    "BTCUSD": (64210.0, 2, 0.01, 900, 1.0, "Bitcoin vs US Dollar"),
    "USDCAD": (1.3654, 5, 0.00001, 18, 0.73, "US Dollar vs Canadian Dollar"),
    "AUDUSD": (0.6612, 5, 0.00001, 14, 1.0, "Australian Dollar vs US Dollar"),
    "US30": (39250.0, 1, 0.1, 30, 0.1, "Dow Jones Index"),
}

_state = {}
_positions = {}
_orders = {}
_deals = []
_ticket = [50000]
_balance = [10000.0]
_started = False


def _init_state():
    now = time.time()
    for name, (price, digits, point, spread, tv, desc) in _SPECS.items():
        _state[name] = {
            "price": price, "digits": digits, "point": point,
            "spread": spread, "tick_value": tv, "description": desc,
            "visible": name in ("EURUSD", "GBPUSD", "XAUUSD", "USDJPY", "BTCUSD"),
            "seed": random.Random(name), "last_move": now,
        }


def _tick(name):
    st = _state[name]
    now = time.time()
    dt = max(0.0, now - st["last_move"])
    st["last_move"] = now
    # gentle random walk, scaled by the instrument's own volatility
    vol = st["price"] * 0.00004 * math.sqrt(max(dt, 0.2))
    st["price"] = max(st["point"] * 10, st["price"] + st["seed"].gauss(0, vol))
    half = st["spread"] * st["point"] / 2.0
    d = st["digits"]
    return round(st["price"] - half, d), round(st["price"] + half, d)


def _sym(name):
    if name not in _state:
        raise BridgeError("Unknown symbol: %s" % name)
    st = _state[name]
    bid, ask = _tick(name)
    return {
        "symbol": name,
        "description": st["description"],
        "path": "Demo\\%s" % name,
        "digits": st["digits"],
        "point": st["point"],
        "bid": bid,
        "ask": ask,
        "last": bid,
        "spread": st["spread"],
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "trade_contract_size": 100000.0,
        "trade_tick_value": st["tick_value"],
        "trade_tick_size": st["point"],
        "stops_level": 0,
        "visible": st["visible"],
    }


# --------------------------------------------------------------------------

def start(terminal_path=None, login=None, password=None, server=None):
    global _started
    with _lock:
        if not _state:
            _init_state()
        _started = True
    return status()


def stop():
    global _started
    _started = False


def status():
    return {
        "connected": _started,
        "demo": True,
        "terminal": {"name": "Demo Terminal", "company": "mt5-panel offline demo",
                     "build": 0, "trade_allowed": True, "connected": _started},
        "account": account() if _started else None,
    }


def account():
    profit = sum(p["profit"] for p in _live_positions())
    bal = _balance[0]
    margin = sum(p["volume"] for p in _live_positions()) * 300.0
    equity = bal + profit
    return {
        "login": 5000123, "name": "Demo Account", "server": "Demo-Server",
        "currency": "USD", "leverage": 500, "balance": round(bal, 2),
        "equity": round(equity, 2), "profit": round(profit, 2),
        "margin": round(margin, 2), "margin_free": round(equity - margin, 2),
        "margin_level": round(equity / margin * 100, 2) if margin else 0.0,
        "trade_allowed": True,
    }


def symbols(watch_only=True, search=""):
    out = []
    for name, st in _state.items():
        if watch_only and not st["visible"]:
            continue
        if search and search.lower() not in name.lower() \
                and search.lower() not in st["description"].lower():
            continue
        out.append(_sym(name))
    return out


def symbol_info(symbol):
    return _sym(symbol)


def select_symbol(symbol, enable=True):
    if symbol not in _state:
        raise BridgeError("Unknown symbol: %s" % symbol)
    _state[symbol]["visible"] = bool(enable)
    return {"symbol": symbol, "visible": bool(enable)}


_TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600,
               "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000}


def candles(symbol, timeframe="M15", count=200):
    if symbol not in _state:
        raise BridgeError("Unknown symbol: %s" % symbol)
    step = _TF_SECONDS.get(str(timeframe).upper())
    if step is None:
        raise BridgeError("Unknown timeframe: %s" % timeframe)
    st = _state[symbol]
    count = int(count)
    rng = random.Random("%s-%s" % (symbol, timeframe))
    now = int(time.time() // step * step)
    price = st["price"]
    bars = []
    # walk backwards from the current price, then flip so time ascends
    for i in range(count):
        drift = price * 0.0025
        o = price
        c = price + rng.gauss(0, drift)
        h = max(o, c) + abs(rng.gauss(0, drift * 0.6))
        l = min(o, c) - abs(rng.gauss(0, drift * 0.6))
        d = st["digits"]
        bars.append({"t": now - i * step, "o": round(o, d), "h": round(h, d),
                     "l": round(l, d), "c": round(c, d),
                     "v": rng.randint(200, 4000)})
        price = c
    bars.reverse()
    return bars


# --------------------------------------------------------------------------

def _live_positions():
    out = []
    for tk, p in list(_positions.items()):
        s = _sym(p["symbol"])
        cur = s["bid"] if p["type"] == "buy" else s["ask"]
        pip = (cur - p["price_open"]) if p["type"] == "buy" else (p["price_open"] - cur)
        profit = pip / s["trade_tick_size"] * s["trade_tick_value"] * p["volume"]
        out.append(dict(p, price_current=cur, profit=round(profit, 2),
                        digits=s["digits"]))
        _check_sl_tp(tk, p, cur, profit)
    return out


def _check_sl_tp(ticket, p, cur, profit):
    hit = None
    if p["type"] == "buy":
        if p["sl"] and cur <= p["sl"]:
            hit = "sl"
        elif p["tp"] and cur >= p["tp"]:
            hit = "tp"
    else:
        if p["sl"] and cur >= p["sl"]:
            hit = "sl"
        elif p["tp"] and cur <= p["tp"]:
            hit = "tp"
    if hit:
        _settle(ticket, p["volume"], cur, profit, comment=hit)


def positions():
    return sorted(_live_positions(), key=lambda x: x["time"], reverse=True)


def pending_orders():
    return sorted(_orders.values(), key=lambda x: x["time"], reverse=True)


def history(days=30):
    cutoff = time.time() - int(days) * 86400
    deals = [d for d in _deals if d["time"] >= cutoff]
    deals.sort(key=lambda x: x["time"], reverse=True)
    from mt5_bridge import _totals
    return {"deals": deals, "totals": _totals(deals)}


def normalize_volume(info, volume):
    return max(0.01, min(100.0, round(float(volume) / 0.01) * 0.01))


def market_order(symbol, side, volume, sl=None, tp=None,
                 deviation=20, comment="mt5-panel"):
    side = str(side).lower()
    if side not in ("buy", "sell"):
        raise BridgeError("side must be buy or sell")
    s = _sym(symbol)
    vol = round(max(0.01, float(volume)), 2)
    _ticket[0] += 1
    tk = _ticket[0]
    _positions[tk] = {
        "ticket": tk, "symbol": symbol, "type": side, "volume": vol,
        "price_open": s["ask"] if side == "buy" else s["bid"],
        "price_current": s["bid"] if side == "buy" else s["ask"],
        "sl": float(sl) if sl else 0.0, "tp": float(tp) if tp else 0.0,
        "profit": 0.0, "swap": 0.0, "time": int(time.time()),
        "comment": comment, "digits": s["digits"],
    }
    return {"retcode": 10009, "deal": tk, "order": tk,
            "price": _positions[tk]["price_open"], "volume": vol,
            "comment": "demo filled"}


def pending_order(symbol, order_type, volume, price, sl=None, tp=None,
                  comment="mt5-panel"):
    s = _sym(symbol)
    _ticket[0] += 1
    tk = _ticket[0]
    _orders[tk] = {
        "ticket": tk, "symbol": symbol, "type": str(order_type).lower(),
        "volume": round(float(volume), 2), "price_open": float(price),
        "sl": float(sl) if sl else 0.0, "tp": float(tp) if tp else 0.0,
        "time": int(time.time()), "digits": s["digits"],
    }
    return {"retcode": 10009, "deal": 0, "order": tk, "price": float(price),
            "volume": float(volume), "comment": "demo placed"}


def modify_position(ticket, sl=None, tp=None):
    p = _positions.get(int(ticket))
    if not p:
        raise BridgeError("Position %s not found" % ticket)
    p["sl"] = float(sl) if sl else 0.0
    p["tp"] = float(tp) if tp else 0.0
    return {"retcode": 10009, "deal": 0, "order": int(ticket), "price": 0,
            "volume": p["volume"], "comment": "demo modified"}


def _settle(ticket, volume, price, profit, comment="close"):
    p = _positions.get(int(ticket))
    if not p:
        return
    part = min(float(volume), p["volume"])
    share = profit * (part / p["volume"]) if p["volume"] else 0.0
    _balance[0] += share
    _deals.append({
        "ticket": _ticket[0] + 1, "position": ticket, "symbol": p["symbol"],
        "type": p["type"], "volume": round(part, 2), "price": price,
        "profit": round(share, 2), "commission": 0.0, "swap": 0.0,
        "net": round(share, 2), "time": int(time.time()), "comment": comment,
    })
    _ticket[0] += 1
    if part >= p["volume"] - 1e-9:
        _positions.pop(int(ticket), None)
    else:
        p["volume"] = round(p["volume"] - part, 2)


def close_position(ticket, volume=None, deviation=20):
    ticket = int(ticket)
    p = _positions.get(ticket)
    if not p:
        raise BridgeError("Position %s not found" % ticket)
    s = _sym(p["symbol"])
    cur = s["bid"] if p["type"] == "buy" else s["ask"]
    pip = (cur - p["price_open"]) if p["type"] == "buy" else (p["price_open"] - cur)
    profit = pip / s["trade_tick_size"] * s["trade_tick_value"] * p["volume"]
    vol = p["volume"] if volume in (None, "", 0) else float(volume)
    _settle(ticket, vol, cur, profit)
    return {"retcode": 10009, "deal": ticket, "order": ticket, "price": cur,
            "volume": vol, "comment": "demo closed"}


def close_all(symbol=None):
    results = []
    for tk in list(_positions):
        if symbol and _positions[tk]["symbol"] != symbol:
            continue
        results.append({"ticket": tk, "ok": True, "result": close_position(tk)})
    return {"closed": results}


def cancel_order(ticket):
    if int(ticket) not in _orders:
        raise BridgeError("Order %s not found" % ticket)
    _orders.pop(int(ticket))
    return {"retcode": 10009, "deal": 0, "order": int(ticket), "price": 0,
            "volume": 0, "comment": "demo cancelled"}


def calc_lot(symbol, risk_amount, sl_points):
    s = _sym(symbol)
    sl_points = float(sl_points)
    if sl_points <= 0:
        raise BridgeError("Stop loss distance must be greater than zero.")
    loss_per_lot = sl_points * s["point"] / s["trade_tick_size"] * s["trade_tick_value"]
    raw = float(risk_amount) / loss_per_lot
    lot = max(0.01, round(raw / 0.01) * 0.01)
    return {"symbol": symbol, "lot": round(lot, 2), "raw_lot": raw,
            "loss_per_lot": loss_per_lot, "estimated_loss": lot * loss_per_lot,
            "volume_min": 0.01, "volume_step": 0.01}
