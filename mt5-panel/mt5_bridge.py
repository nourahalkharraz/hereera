"""Thin wrapper around the official MetaTrader5 python package.

Every function returns plain dicts/lists so the HTTP layer can serialise them
straight to JSON. Errors are raised as BridgeError with a readable message.
"""

from datetime import datetime, timedelta, timezone

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - only importable on Windows
    mt5 = None


class BridgeError(Exception):
    pass


TIMEFRAMES = {}
if mt5 is not None:
    TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

DEMO = False
_started = False


# --------------------------------------------------------------------------
# lifecycle
# --------------------------------------------------------------------------

def start(terminal_path=None, login=None, password=None, server=None):
    """Attach to the MT5 terminal running on this PC."""
    global _started
    if mt5 is None:
        raise BridgeError(
            "MetaTrader5 package is not installed (Windows only). "
            "Run: pip install MetaTrader5"
        )
    kwargs = {}
    if terminal_path:
        kwargs["path"] = terminal_path
    if login:
        kwargs["login"] = int(login)
        kwargs["password"] = password or ""
        kwargs["server"] = server or ""
    ok = mt5.initialize(**kwargs)
    if not ok:
        raise BridgeError("initialize() failed: %s" % (mt5.last_error(),))
    _started = True
    return status()


def stop():
    global _started
    if mt5 is not None and _started:
        mt5.shutdown()
        _started = False


def _need():
    if mt5 is None:
        raise BridgeError("MetaTrader5 package is not available on this machine.")
    if not _started:
        raise BridgeError("Not connected to the MT5 terminal.")


def status():
    if mt5 is None:
        return {"connected": False, "demo": False,
                "error": "MetaTrader5 package not installed"}
    if not _started:
        return {"connected": False, "demo": False, "error": "not initialized"}
    term = mt5.terminal_info()
    acc = mt5.account_info()
    return {
        "connected": bool(term and acc),
        "demo": False,
        "terminal": {
            "name": getattr(term, "name", ""),
            "company": getattr(term, "company", ""),
            "build": getattr(term, "build", 0),
            "trade_allowed": bool(getattr(term, "trade_allowed", False)),
            "connected": bool(getattr(term, "connected", False)),
        } if term else None,
        "account": account() if acc else None,
    }


# --------------------------------------------------------------------------
# account / symbols / quotes
# --------------------------------------------------------------------------

def account():
    _need()
    a = mt5.account_info()
    if a is None:
        raise BridgeError("account_info() returned nothing: %s" % (mt5.last_error(),))
    return {
        "login": a.login,
        "name": a.name,
        "server": a.server,
        "currency": a.currency,
        "leverage": a.leverage,
        "balance": a.balance,
        "equity": a.equity,
        "profit": a.profit,
        "margin": a.margin,
        "margin_free": a.margin_free,
        "margin_level": a.margin_level,
        "trade_allowed": bool(a.trade_allowed),
    }


def _sym_payload(info, tick):
    bid = getattr(tick, "bid", 0.0) if tick else 0.0
    ask = getattr(tick, "ask", 0.0) if tick else 0.0
    digits = info.digits
    point = info.point
    spread_pts = round((ask - bid) / point) if point else 0
    return {
        "symbol": info.name,
        "description": info.description,
        "path": info.path,
        "digits": digits,
        "point": point,
        "bid": bid,
        "ask": ask,
        "last": getattr(tick, "last", 0.0) if tick else 0.0,
        "spread": spread_pts,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "trade_contract_size": info.trade_contract_size,
        "trade_tick_value": info.trade_tick_value,
        "trade_tick_size": info.trade_tick_size,
        "stops_level": info.trade_stops_level,
        "visible": bool(info.visible),
    }


def symbols(watch_only=True, search=""):
    """Market Watch symbols (watch_only) or the broker's full list."""
    _need()
    if watch_only:
        items = [s for s in (mt5.symbols_get() or []) if s.visible]
    else:
        items = list(mt5.symbols_get() or [])
    if search:
        q = search.lower()
        items = [s for s in items
                 if q in s.name.lower() or q in (s.description or "").lower()]
        items = items[:300]
    out = []
    for info in items:
        tick = mt5.symbol_info_tick(info.name) if info.visible else None
        out.append(_sym_payload(info, tick))
    return out


def symbol_info(symbol):
    _need()
    info = mt5.symbol_info(symbol)
    if info is None:
        raise BridgeError("Unknown symbol: %s" % symbol)
    if not info.visible:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    return _sym_payload(info, mt5.symbol_info_tick(symbol))


def select_symbol(symbol, enable=True):
    _need()
    if not mt5.symbol_select(symbol, bool(enable)):
        raise BridgeError("symbol_select failed: %s" % (mt5.last_error(),))
    return {"symbol": symbol, "visible": bool(enable)}


def candles(symbol, timeframe="M15", count=200):
    _need()
    tf = TIMEFRAMES.get(str(timeframe).upper())
    if tf is None:
        raise BridgeError("Unknown timeframe: %s" % timeframe)
    if mt5.symbol_info(symbol) is None:
        raise BridgeError("Unknown symbol: %s" % symbol)
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, int(count))
    if rates is None:
        raise BridgeError("copy_rates failed: %s" % (mt5.last_error(),))
    return [
        {"t": int(r["time"]), "o": float(r["open"]), "h": float(r["high"]),
         "l": float(r["low"]), "c": float(r["close"]), "v": int(r["tick_volume"])}
        for r in rates
    ]


# --------------------------------------------------------------------------
# positions / orders / history
# --------------------------------------------------------------------------

def positions():
    _need()
    out = []
    for p in (mt5.positions_get() or []):
        info = mt5.symbol_info(p.symbol)
        out.append({
            "ticket": p.ticket,
            "symbol": p.symbol,
            "type": "buy" if p.type == mt5.POSITION_TYPE_BUY else "sell",
            "volume": p.volume,
            "price_open": p.price_open,
            "price_current": p.price_current,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
            "swap": p.swap,
            "time": int(p.time),
            "comment": p.comment,
            "digits": info.digits if info else 5,
        })
    out.sort(key=lambda x: x["time"], reverse=True)
    return out


ORDER_TYPE_NAMES = {}
if mt5 is not None:
    ORDER_TYPE_NAMES = {
        mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
        mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
        mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
    }


def pending_orders():
    _need()
    out = []
    for o in (mt5.orders_get() or []):
        info = mt5.symbol_info(o.symbol)
        out.append({
            "ticket": o.ticket,
            "symbol": o.symbol,
            "type": ORDER_TYPE_NAMES.get(o.type, str(o.type)),
            "volume": o.volume_current,
            "price_open": o.price_open,
            "sl": o.sl,
            "tp": o.tp,
            "time": int(o.time_setup),
            "digits": info.digits if info else 5,
        })
    out.sort(key=lambda x: x["time"], reverse=True)
    return out


def history(days=30):
    """Closed trades (deals with entry=OUT) over the last N days."""
    _need()
    now = datetime.now(timezone.utc) + timedelta(days=1)
    frm = now - timedelta(days=int(days) + 1)
    deals = mt5.history_deals_get(frm, now)
    if deals is None:
        return {"deals": [], "totals": _totals([])}
    out = []
    for d in deals:
        if d.entry != mt5.DEAL_ENTRY_OUT and d.entry != mt5.DEAL_ENTRY_OUT_BY:
            continue
        out.append({
            "ticket": d.ticket,
            "position": d.position_id,
            "symbol": d.symbol,
            # a closing deal is the opposite side of the position it closed
            "type": "sell" if d.type == mt5.DEAL_TYPE_BUY else "buy",
            "volume": d.volume,
            "price": d.price,
            "profit": d.profit,
            "commission": d.commission,
            "swap": d.swap,
            "net": d.profit + d.commission + d.swap,
            "time": int(d.time),
            "comment": d.comment,
        })
    out.sort(key=lambda x: x["time"], reverse=True)
    return {"deals": out, "totals": _totals(out)}


def _totals(deals):
    wins = [d for d in deals if d["net"] > 0]
    losses = [d for d in deals if d["net"] < 0]
    gross_win = sum(d["net"] for d in wins)
    gross_loss = -sum(d["net"] for d in losses)
    return {
        "count": len(deals),
        "net": sum(d["net"] for d in deals),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(deals) * 100.0) if deals else 0.0,
        "best": max((d["net"] for d in deals), default=0.0),
        "worst": min((d["net"] for d in deals), default=0.0),
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "profit_factor": (gross_win / gross_loss) if gross_loss else 0.0,
        "volume": sum(d["volume"] for d in deals),
    }


# --------------------------------------------------------------------------
# trading
# --------------------------------------------------------------------------

def _filling_mode(info):
    modes = info.filling_mode
    if modes & 1:  # SYMBOL_FILLING_FOK
        return mt5.ORDER_FILLING_FOK
    if modes & 2:  # SYMBOL_FILLING_IOC
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def normalize_volume(info, volume):
    step = info.volume_step or 0.01
    vol = round(round(float(volume) / step) * step, 8)
    vol = max(info.volume_min, min(info.volume_max, vol))
    # kill float dust such as 0.30000000000000004
    decimals = max(0, len(str(step).split(".")[-1])) if "." in str(step) else 0
    return round(vol, decimals)


def _check(result, action):
    if result is None:
        raise BridgeError("%s failed: %s" % (action, mt5.last_error()))
    if result.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        raise BridgeError("%s rejected (%s): %s"
                          % (action, result.retcode, result.comment))
    return {
        "retcode": result.retcode,
        "deal": result.deal,
        "order": result.order,
        "price": result.price,
        "volume": result.volume,
        "comment": result.comment,
    }


def market_order(symbol, side, volume, sl=None, tp=None,
                 deviation=20, comment="mt5-panel"):
    _need()
    info = mt5.symbol_info(symbol)
    if info is None:
        raise BridgeError("Unknown symbol: %s" % symbol)
    if not info.visible:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise BridgeError("No price for %s" % symbol)

    side = str(side).lower()
    if side not in ("buy", "sell"):
        raise BridgeError("side must be buy or sell")
    is_buy = side == "buy"
    price = tick.ask if is_buy else tick.bid

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": normalize_volume(info, volume),
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": price,
        "deviation": int(deviation),
        "magic": 777001,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(info),
    }
    if sl:
        req["sl"] = round(float(sl), info.digits)
    if tp:
        req["tp"] = round(float(tp), info.digits)
    return _check(mt5.order_send(req), "market order")


PENDING_TYPES = {}
if mt5 is not None:
    PENDING_TYPES = {
        "buy_limit": mt5.ORDER_TYPE_BUY_LIMIT,
        "sell_limit": mt5.ORDER_TYPE_SELL_LIMIT,
        "buy_stop": mt5.ORDER_TYPE_BUY_STOP,
        "sell_stop": mt5.ORDER_TYPE_SELL_STOP,
    }


def pending_order(symbol, order_type, volume, price,
                  sl=None, tp=None, comment="mt5-panel"):
    _need()
    otype = PENDING_TYPES.get(str(order_type).lower())
    if otype is None:
        raise BridgeError("Unknown pending order type: %s" % order_type)
    info = mt5.symbol_info(symbol)
    if info is None:
        raise BridgeError("Unknown symbol: %s" % symbol)
    if not info.visible:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    req = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": normalize_volume(info, volume),
        "type": otype,
        "price": round(float(price), info.digits),
        "magic": 777001,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(info),
    }
    if sl:
        req["sl"] = round(float(sl), info.digits)
    if tp:
        req["tp"] = round(float(tp), info.digits)
    return _check(mt5.order_send(req), "pending order")


def modify_position(ticket, sl=None, tp=None):
    _need()
    pos = mt5.positions_get(ticket=int(ticket))
    if not pos:
        raise BridgeError("Position %s not found" % ticket)
    pos = pos[0]
    info = mt5.symbol_info(pos.symbol)
    req = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": int(ticket),
        "symbol": pos.symbol,
        "sl": round(float(sl), info.digits) if sl else 0.0,
        "tp": round(float(tp), info.digits) if tp else 0.0,
    }
    return _check(mt5.order_send(req), "modify")


def close_position(ticket, volume=None, deviation=20):
    _need()
    pos = mt5.positions_get(ticket=int(ticket))
    if not pos:
        raise BridgeError("Position %s not found" % ticket)
    pos = pos[0]
    info = mt5.symbol_info(pos.symbol)
    tick = mt5.symbol_info_tick(pos.symbol)
    is_buy = pos.type == mt5.POSITION_TYPE_BUY
    vol = pos.volume if volume in (None, "", 0) else min(
        normalize_volume(info, volume), pos.volume)
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "position": int(ticket),
        "volume": vol,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": int(deviation),
        "magic": 777001,
        "comment": "close by mt5-panel",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _filling_mode(info),
    }
    return _check(mt5.order_send(req), "close")


def close_all(symbol=None):
    _need()
    results = []
    for p in (mt5.positions_get() or []):
        if symbol and p.symbol != symbol:
            continue
        try:
            results.append({"ticket": p.ticket, "ok": True,
                            "result": close_position(p.ticket)})
        except BridgeError as exc:
            results.append({"ticket": p.ticket, "ok": False, "error": str(exc)})
    return {"closed": results}


def cancel_order(ticket):
    _need()
    req = {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)}
    return _check(mt5.order_send(req), "cancel")


# --------------------------------------------------------------------------
# risk helper
# --------------------------------------------------------------------------

def calc_lot(symbol, risk_amount, sl_points):
    """Lot size so that hitting `sl_points` away loses about `risk_amount`."""
    _need()
    info = mt5.symbol_info(symbol)
    if info is None:
        raise BridgeError("Unknown symbol: %s" % symbol)
    sl_points = float(sl_points)
    if sl_points <= 0:
        raise BridgeError("Stop loss distance must be greater than zero.")
    tick_value = info.trade_tick_value
    tick_size = info.trade_tick_size or info.point
    if not tick_value or not tick_size:
        raise BridgeError("Broker did not report tick value for %s" % symbol)
    # loss for 1 lot = distance in price / tick size * tick value
    price_distance = sl_points * info.point
    loss_per_lot = price_distance / tick_size * tick_value
    if loss_per_lot <= 0:
        raise BridgeError("Could not compute risk for %s" % symbol)
    raw = float(risk_amount) / loss_per_lot
    lot = normalize_volume(info, raw)
    return {
        "symbol": symbol,
        "lot": lot,
        "raw_lot": raw,
        "loss_per_lot": loss_per_lot,
        "estimated_loss": lot * loss_per_lot,
        "volume_min": info.volume_min,
        "volume_step": info.volume_step,
    }
