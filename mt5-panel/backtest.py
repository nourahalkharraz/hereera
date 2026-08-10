"""Replay the strategy over historical candles.

Same entry logic as the live engine and the same trade management (partial at
1R, break-even, ATR trail), so the numbers here describe the thing that will
actually run — not a simplified cousin of it.

Honest about its limits, which matter more than the headline win rate:

  * Spread is a fixed assumption you supply. Real spreads widen exactly when
    the market moves, which is when the engine wants to trade.
  * Slippage and commission are not modelled. Add them mentally.
  * When a bar touches both the stop and the target, the stop is assumed to
    hit first. Pessimistic on purpose.
  * Past behaviour is not a forecast. A good curve here is a reason to run it
    on paper next, not a reason to go live.
"""

import bisect
import threading
import time

import strategy

WARMUP = 260          # bars of history handed to the analyser each step


def run(bridge, cfg, progress=None, should_stop=None):
    symbol = cfg.get("symbol") or "XAUUSD"
    entry_tf = cfg.get("entry_tf", "M5")
    trend_tf = cfg.get("trend_tf", "M15")
    bars = int(cfg.get("bars", 5000))
    spread_points = float(cfg.get("spread_points", 25))
    risk_percent = float(cfg.get("risk_percent", 0.5))
    start_balance = float(cfg.get("balance", 10000))
    cooldown_min = float(cfg.get("cooldown_minutes", 15))

    info = bridge.symbol_info(symbol)
    point = info["point"]
    tick_size = info["trade_tick_size"] or point
    tick_value = info["trade_tick_value"]
    spread = spread_points * point

    entry = bridge.candles(symbol, entry_tf, min(bars, 20000))
    trend = bridge.candles(symbol, trend_tf, min(bars, 20000))
    if len(entry) < WARMUP + 50 or len(trend) < 80:
        raise ValueError("Not enough history for %s on %s" % (symbol, entry_tf))

    trend_times = [c["t"] for c in trend]
    scfg = {
        "mode_profile": cfg.get("profile", "scalp"),
        "min_confidence": cfg.get("min_confidence", 72),
        "sl_atr": cfg.get("sl_atr", 1.1),
        "tp_atr": cfg.get("tp_atr", 1.8),
        "sessions": cfg.get("sessions"),
        "blackouts": cfg.get("blackouts"),
        "trade_weekend": cfg.get("trade_weekend", False),
    }
    scfg = {k: v for k, v in scfg.items() if v is not None}

    partial_at = float(cfg.get("partial_at_r", 1.0))
    partial_fraction = float(cfg.get("partial_fraction", 0.5))
    be_at = float(cfg.get("break_even_at_r", 1.0))
    trail_after = float(cfg.get("trail_after_r", 1.3))
    trail_atr = float(cfg.get("trail_atr", 1.0))

    balance = start_balance
    peak = balance
    max_dd = 0.0
    trades = []
    curve = [{"t": entry[WARMUP]["t"], "equity": round(balance, 2)}]
    open_trade = None
    last_exit_t = 0
    skipped = {}

    total = len(entry) - WARMUP - 1
    for i in range(WARMUP, len(entry) - 1):
        if should_stop and should_stop():
            break
        if progress and (i - WARMUP) % 250 == 0:
            progress((i - WARMUP) / float(total or 1))

        bar = entry[i]
        nxt = entry[i + 1]

        # ---- manage an open trade across this bar ------------------------
        if open_trade:
            open_trade, closed = _walk_bar(open_trade, nxt, spread, tick_size,
                                           tick_value, partial_at,
                                           partial_fraction, be_at,
                                           trail_after, trail_atr)
            if closed:
                balance += closed["profit"]
                peak = max(peak, balance)
                max_dd = max(max_dd, peak - balance)
                closed["balance"] = round(balance, 2)
                trades.append(closed)
                curve.append({"t": nxt["t"], "equity": round(balance, 2)})
                last_exit_t = nxt["t"]
            continue

        if bar["t"] - last_exit_t < cooldown_min * 60:
            continue

        # ---- look for an entry on the bar that just closed ---------------
        j = bisect.bisect_right(trend_times, bar["t"])
        if j < 60:
            continue
        d = strategy.analyze(entry[max(0, i - WARMUP + 1):i + 2],
                             trend[max(0, j - WARMUP):j],
                             symbol, spread_price=spread, cfg=scfg,
                             now_ts=bar["t"])
        if not d.get("side"):
            for b in d.get("blockers", [])[:1]:
                skipped[b] = skipped.get(b, 0) + 1
            continue

        # fill at the next bar's open, paying the spread
        fill = nxt["o"] + spread if d["side"] == "buy" else nxt["o"]
        risk_dist = d["sl_points"]
        sl = fill - risk_dist if d["side"] == "buy" else fill + risk_dist
        tp = fill + d["tp_points"] if d["side"] == "buy" else fill - d["tp_points"]

        risk_amount = balance * risk_percent / 100.0
        loss_per_lot = risk_dist / tick_size * tick_value
        if loss_per_lot <= 0:
            continue
        lot = _round_lot(risk_amount / loss_per_lot, info)
        if lot < info["volume_min"] - 1e-9:
            skipped["lot_below_minimum"] = skipped.get("lot_below_minimum", 0) + 1
            continue

        open_trade = {
            "symbol": symbol, "side": d["side"], "volume": lot,
            "open_volume": lot, "price_open": fill, "sl": sl, "tp": tp,
            "initial_sl": sl, "risk_dist": risk_dist, "atr": d["atr"],
            "confidence": d["confidence"], "rr": d.get("rr"),
            "time": nxt["t"], "tick_size": tick_size, "tick_value": tick_value,
            "booked": 0.0, "partial_done": False, "be_done": False,
            "risk_amount": round(lot * loss_per_lot, 2),
        }

    if open_trade:                     # still running at the end of the data
        curve.append({"t": entry[-1]["t"], "equity": round(balance, 2)})

    return {
        "symbol": symbol, "entry_tf": entry_tf, "trend_tf": trend_tf,
        "profile": scfg.get("mode_profile"),
        "bars": len(entry), "spread_points": spread_points,
        "from": entry[WARMUP]["t"], "to": entry[-1]["t"],
        "start_balance": start_balance, "end_balance": round(balance, 2),
        "stats": _summarise(trades, start_balance, balance, max_dd),
        "trades": trades[-200:],
        "curve": _thin(curve, 400),
        "skipped": sorted(skipped.items(), key=lambda kv: -kv[1])[:8],
    }


# --------------------------------------------------------------------------

def _walk_bar(tr, bar, spread, tick_size, tick_value, partial_at,
              partial_fraction, be_at, trail_after, trail_atr):
    """Advance one open trade through a single candle.

    Returns (still_open_or_None, closed_record_or_None).
    """
    buy = tr["side"] == "buy"
    # prices the position is marked at: a long exits on the bid, a short on
    # the ask, so the short's levels sit one spread above the printed candle
    high = bar["h"] if buy else bar["h"] + spread
    low = bar["l"] if buy else bar["l"] + spread

    # stop first when both are inside the same bar — the pessimistic read
    hit_sl = (low <= tr["sl"]) if buy else (high >= tr["sl"])
    if hit_sl:
        return None, _close(tr, tr["sl"], bar["t"], "sl")

    hit_tp = (high >= tr["tp"]) if buy else (low <= tr["tp"])
    if hit_tp:
        return None, _close(tr, tr["tp"], bar["t"], "tp")

    close_price = bar["c"] if buy else bar["c"] + spread
    moved = (close_price - tr["price_open"]) if buy \
        else (tr["price_open"] - close_price)
    r = moved / tr["risk_dist"] if tr["risk_dist"] else 0.0

    if not tr["partial_done"] and partial_fraction > 0 and r >= partial_at:
        part = round(tr["volume"] * partial_fraction, 2)
        if 0 < part < tr["volume"]:
            gain = moved / tick_size * tick_value * part
            tr["booked"] += gain
            tr["volume"] = round(tr["volume"] - part, 2)
        tr["partial_done"] = True

    if not tr["be_done"] and r >= be_at:
        be = tr["price_open"]
        if (be > tr["sl"]) if buy else (be < tr["sl"]):
            tr["sl"] = be
        tr["be_done"] = True

    if r >= trail_after and tr.get("atr"):
        dist = tr["atr"] * trail_atr
        trail = close_price - dist if buy else close_price + dist
        if (trail > tr["sl"]) if buy else (trail < tr["sl"]):
            tr["sl"] = trail

    return tr, None


def _close(tr, price, t, reason):
    buy = tr["side"] == "buy"
    move = (price - tr["price_open"]) if buy else (tr["price_open"] - price)
    profit = move / tr["tick_size"] * tr["tick_value"] * tr["volume"]
    total = profit + tr["booked"]
    return {
        "symbol": tr["symbol"], "side": tr["side"], "volume": tr["open_volume"],
        "price_open": tr["price_open"], "price_close": price,
        "time": tr["time"], "close_time": t, "result": reason,
        "confidence": tr["confidence"], "rr": tr.get("rr"),
        "profit": round(total, 2),
        "r": round(total / tr["risk_amount"], 2) if tr["risk_amount"] else 0.0,
    }


def _round_lot(raw, info):
    step = info["volume_step"] or 0.01
    lot = round(raw / step) * step
    lot = max(info["volume_min"], min(info["volume_max"], lot))
    decimals = len(str(step).split(".")[-1]) if "." in str(step) else 0
    return round(lot, decimals)


def _summarise(trades, start_balance, end_balance, max_dd):
    if not trades:
        return {"count": 0, "win_rate": 0.0, "profit_factor": 0.0,
                "net": 0.0, "net_percent": 0.0, "max_drawdown": 0.0,
                "max_drawdown_percent": 0.0, "expectancy_r": 0.0,
                "avg_win": 0.0, "avg_loss": 0.0, "best": 0.0, "worst": 0.0,
                "longest_losing_streak": 0}
    nets = [t["profit"] for t in trades]
    rs = [t["r"] for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x <= 0]
    gross_win, gross_loss = sum(wins), -sum(losses)
    streak = worst_streak = 0
    for x in nets:
        streak = streak + 1 if x <= 0 else 0
        worst_streak = max(worst_streak, streak)
    return {
        "count": len(trades),
        "win_rate": round(len(wins) / len(nets) * 100.0, 1),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else 0.0,
        "net": round(end_balance - start_balance, 2),
        "net_percent": round((end_balance / start_balance - 1) * 100.0, 2),
        "max_drawdown": round(max_dd, 2),
        "max_drawdown_percent": round(max_dd / start_balance * 100.0, 2),
        "expectancy_r": round(sum(rs) / len(rs), 3),
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "best": round(max(nets), 2), "worst": round(min(nets), 2),
        "longest_losing_streak": worst_streak,
    }


def _thin(points, limit):
    if len(points) <= limit:
        return points
    step = len(points) / float(limit)
    return [points[int(i * step)] for i in range(limit)] + [points[-1]]


# --------------------------------------------------------------------------
# background job, so a long replay never blocks the panel
# --------------------------------------------------------------------------

class BacktestJob(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.lock = threading.Lock()
        self.state = "idle"      # idle | running | done | error
        self.progress = 0.0
        self.result = None
        self.error = ""
        self.started = 0
        self._thread = None
        self._cancel = False

    def start(self, cfg):
        with self.lock:
            if self.state == "running":
                raise RuntimeError("A backtest is already running")
            self.state = "running"
            self.progress = 0.0
            self.result = None
            self.error = ""
            self.started = int(time.time())
            self._cancel = False
        self._thread = threading.Thread(target=self._run, args=(cfg,),
                                        daemon=True)
        self._thread.start()
        return self.status()

    def cancel(self):
        self._cancel = True
        return self.status()

    def _run(self, cfg):
        try:
            res = run(self.bridge, cfg,
                      progress=self._set_progress,
                      should_stop=lambda: self._cancel)
            with self.lock:
                self.result = res
                self.state = "done"
                self.progress = 1.0
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.state = "error"

    def _set_progress(self, value):
        with self.lock:
            self.progress = round(value, 3)

    def status(self):
        with self.lock:
            return {"state": self.state, "progress": self.progress,
                    "error": self.error, "started": self.started,
                    "result": self.result}
