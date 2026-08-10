"""The automatic trader: a background loop around strategy.analyze().

Two things matter more than the signal logic here:

  * It starts in **paper** mode. Signals are recorded and tracked against real
    prices, but no order reaches the broker until the mode is switched to
    "live" deliberately.
  * Every trade passes the risk manager first — position size derived from a
    risk percentage, a mandatory stop loss, a cap on open and daily trades,
    and a daily loss limit that shuts the engine off for the rest of the day.

State (config, paper trades, counters) is kept in bot_state.json so a restart
does not reset the daily limits.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone

import strategy

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "bot_state.json")

DEFAULT_CONFIG = {
    "mode": "paper",             # paper | live
    "symbols": [],               # empty = whatever is in Market Watch (max 6)
    "entry_tf": "M15",
    "trend_tf": "H1",
    "min_confidence": 70,        # 0-100, from strategy.analyze
    "risk_percent": 0.5,         # of balance, per trade
    "max_open": 1,               # concurrent bot positions
    "max_daily_trades": 3,
    "daily_loss_percent": 2.0,   # stop for the day after losing this much
    "cooldown_minutes": 60,      # per symbol, after a trade
    "interval_seconds": 20,      # how often the market is re-studied
    "sl_atr": 1.5,
    "tp_atr": 2.5,
}

MAX_LOG = 300


class AutoTrader(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.lock = threading.RLock()
        self.running = False
        self.halted_reason = ""      # set when a limit stops the engine
        self.config = dict(DEFAULT_CONFIG)
        self.log = []
        self.scan = {}               # symbol -> latest analysis
        self.paper_open = []
        self.paper_closed = []
        self.day = _today()
        self.counters = {"trades": 0, "realised": 0.0}
        self.last_trade_at = {}      # symbol -> unix seconds
        self.last_cycle = 0
        self.cycle_error = ""
        self._thread = None
        self._stop = threading.Event()
        self._load()

    # ------------------------------------------------------------ persistence
    def _load(self):
        if not os.path.isfile(STATE_PATH):
            return
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        except (ValueError, OSError):
            return
        self.config.update({k: v for k, v in d.get("config", {}).items()
                            if k in DEFAULT_CONFIG})
        self.log = d.get("log", [])[-MAX_LOG:]
        self.paper_open = d.get("paper_open", [])
        self.paper_closed = d.get("paper_closed", [])[-500:]
        self.last_trade_at = d.get("last_trade_at", {})
        self.day = d.get("day", _today())
        self.counters = d.get("counters", {"trades": 0, "realised": 0.0})
        self.halted_reason = d.get("halted_reason", "")
        self._roll_day()

    def _save(self):
        tmp = STATE_PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({
                    "config": self.config, "log": self.log[-MAX_LOG:],
                    "paper_open": self.paper_open,
                    "paper_closed": self.paper_closed[-500:],
                    "last_trade_at": self.last_trade_at, "day": self.day,
                    "counters": self.counters,
                    "halted_reason": self.halted_reason,
                }, fh, ensure_ascii=False)
            os.replace(tmp, STATE_PATH)
        except OSError:
            pass

    # ------------------------------------------------------------------ log
    def _event(self, kind, message, **extra):
        entry = {"time": int(time.time()), "kind": kind, "message": message}
        entry.update(extra)
        with self.lock:
            self.log.append(entry)
            self.log = self.log[-MAX_LOG:]
        return entry

    # --------------------------------------------------------------- control
    def start(self):
        with self.lock:
            self._roll_day()
            if self.halted_reason:
                raise RuntimeError(self.halted_reason)
            if self.running:
                return self.status()
            self.running = True
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        self._event("start", "engine started in %s mode" % self.config["mode"])
        self._save()
        return self.status()

    def stop(self, reason="stopped by user"):
        with self.lock:
            was = self.running
            self.running = False
            self._stop.set()
        if was:
            self._event("stop", reason)
            self._save()
        return self.status()

    def set_config(self, updates):
        with self.lock:
            for k, v in (updates or {}).items():
                if k not in DEFAULT_CONFIG:
                    continue
                if k == "mode":
                    if v not in ("paper", "live"):
                        raise ValueError("mode must be paper or live")
                    if v != self.config["mode"]:
                        self._event("mode", "mode changed to %s" % v)
                elif k == "symbols":
                    v = [str(x) for x in (v or [])][:12]
                elif isinstance(DEFAULT_CONFIG[k], bool):
                    v = bool(v)
                elif isinstance(DEFAULT_CONFIG[k], int):
                    v = int(v)
                elif isinstance(DEFAULT_CONFIG[k], float):
                    v = float(v)
                self.config[k] = v
            _clamp(self.config)
            self._save()
        return self.status()

    def clear_halt(self):
        with self.lock:
            self.halted_reason = ""
            self._save()
        return self.status()

    # ---------------------------------------------------------------- status
    def status(self):
        with self.lock:
            paper = [dict(p) for p in self.paper_open]
        floating = 0.0
        for p in paper:
            try:
                info = self.bridge.symbol_info(p["symbol"])
                p["price_current"] = info["bid"] if p["side"] == "buy" else info["ask"]
                p["profit"] = _paper_profit(p, info)
                floating += p["profit"]
            except Exception:
                p["price_current"] = p["price_open"]
                p["profit"] = 0.0
        with self.lock:
            return {
                "running": self.running,
                "halted_reason": self.halted_reason,
                "config": dict(self.config),
                "defaults": dict(DEFAULT_CONFIG),
                "day": self.day,
                "counters": dict(self.counters),
                "floating": floating,
                "paper_open": paper,
                "paper_closed": self.paper_closed[-40:],
                "scan": dict(self.scan),
                "log": self.log[-60:],
                "last_cycle": self.last_cycle,
                "cycle_error": self.cycle_error,
            }

    # ------------------------------------------------------------------ loop
    def _loop(self):
        while not self._stop.is_set():
            try:
                self._cycle()
                self.cycle_error = ""
            except Exception as exc:          # never let the thread die
                self.cycle_error = str(exc)
            self.last_cycle = int(time.time())
            self._stop.wait(max(5, int(self.config["interval_seconds"])))

    def _cycle(self):
        self._roll_day()
        self._update_paper_positions()

        if self.halted_reason:
            self.stop(self.halted_reason)
            return

        # daily loss limit -------------------------------------------------
        account = self.bridge.account()
        realised = self.counters["realised"]
        limit = account["balance"] * self.config["daily_loss_percent"] / 100.0
        if limit > 0 and realised <= -limit:
            self._halt("daily_loss_limit_reached")
            return
        if self.counters["trades"] >= self.config["max_daily_trades"]:
            return

        open_count = len(self._bot_positions())
        if open_count >= self.config["max_open"]:
            return

        for sym in self._symbols():
            if self._stop.is_set():
                return
            try:
                decision = self._study(sym)
            except Exception as exc:
                self.scan[sym] = {"symbol": sym, "error": str(exc),
                                  "time": int(time.time())}
                continue
            if not decision.get("side"):
                continue
            if self._blocked_by_risk(sym):
                continue
            self._take(sym, decision)
            return          # one trade per cycle, then re-evaluate everything

    # ---------------------------------------------------------------- pieces
    def _symbols(self):
        chosen = self.config["symbols"]
        if chosen:
            return chosen[:12]
        try:
            return [s["symbol"] for s in self.bridge.symbols(watch_only=True)][:6]
        except Exception:
            return []

    def _study(self, sym):
        info = self.bridge.symbol_info(sym)
        entry = self.bridge.candles(sym, self.config["entry_tf"], 220)
        trend = self.bridge.candles(sym, self.config["trend_tf"], 220)
        d = strategy.analyze(entry, trend, sym,
                             spread_price=max(0.0, info["ask"] - info["bid"]),
                             cfg={
                                 "min_confidence": self.config["min_confidence"],
                                 "sl_atr": self.config["sl_atr"],
                                 "tp_atr": self.config["tp_atr"],
                             })
        d["time"] = int(time.time())
        d["digits"] = info["digits"]
        self.scan[sym] = d
        return d

    def _bot_positions(self):
        """Open positions the engine is responsible for."""
        if self.config["mode"] == "paper":
            return list(self.paper_open)
        try:
            return [p for p in self.bridge.positions()
                    if str(p.get("comment", "")).startswith("bot")]
        except Exception:
            return []

    def _blocked_by_risk(self, sym):
        now = time.time()
        last = self.last_trade_at.get(sym, 0)
        if now - last < self.config["cooldown_minutes"] * 60:
            return True
        for p in self._bot_positions():
            if p["symbol"] == sym:
                return True
        if self.config["mode"] == "live":
            try:
                if any(p["symbol"] == sym for p in self.bridge.positions()):
                    return True     # never stack on a manual position
            except Exception:
                return True
        return False

    def _take(self, sym, d):
        info = self.bridge.symbol_info(sym)
        account = self.bridge.account()
        side = d["side"]
        entry = info["ask"] if side == "buy" else info["bid"]
        sl_points = d["sl_points"] / info["point"]
        risk_amount = account["balance"] * self.config["risk_percent"] / 100.0

        try:
            calc = self.bridge.calc_lot(sym, risk_amount, sl_points)
        except Exception as exc:
            self._event("skip", "could not size the trade on %s: %s" % (sym, exc),
                        symbol=sym)
            return
        lot = calc["lot"]
        if lot < info["volume_min"] - 1e-9:
            self._event("skip", "risk budget smaller than the minimum lot on %s" % sym,
                        symbol=sym)
            return
        # a rounded-up minimum lot can overshoot the intended risk
        if calc["estimated_loss"] > risk_amount * 1.5:
            self._event("skip",
                        "minimum lot on %s would risk %.2f, over the budget %.2f"
                        % (sym, calc["estimated_loss"], risk_amount), symbol=sym)
            return

        sl = entry - d["sl_points"] if side == "buy" else entry + d["sl_points"]
        tp = entry + d["tp_points"] if side == "buy" else entry - d["tp_points"]
        sl = round(sl, info["digits"])
        tp = round(tp, info["digits"])

        record = {
            "symbol": sym, "side": side, "volume": lot,
            "price_open": entry, "sl": sl, "tp": tp,
            "confidence": d["confidence"], "reasons": d["reasons"],
            "time": int(time.time()), "digits": info["digits"],
            "risk": calc["estimated_loss"], "mode": self.config["mode"],
        }

        if self.config["mode"] == "paper":
            with self.lock:
                self.paper_open.append(record)
        else:
            try:
                res = self.bridge.market_order(
                    symbol=sym, side=side, volume=lot, sl=sl, tp=tp,
                    comment="bot%d" % d["confidence"])
                record["ticket"] = res.get("order")
                record["price_open"] = res.get("price") or entry
            except Exception as exc:
                self._event("error", "order rejected on %s: %s" % (sym, exc),
                            symbol=sym)
                return

        with self.lock:
            self.counters["trades"] += 1
            self.last_trade_at[sym] = time.time()
        self._event("trade", "%s %s %.2f lots at %.*f (confidence %d%%)"
                    % (side, sym, lot, info["digits"], record["price_open"],
                       d["confidence"]),
                    symbol=sym, side=side, confidence=d["confidence"],
                    volume=lot, sl=sl, tp=tp, mode=self.config["mode"],
                    reasons=d["reasons"])
        self._save()

    def _update_paper_positions(self):
        """Mark paper trades to market and close them on SL/TP."""
        if not self.paper_open:
            return
        still_open = []
        for p in list(self.paper_open):
            try:
                info = self.bridge.symbol_info(p["symbol"])
            except Exception:
                still_open.append(p)
                continue
            price = info["bid"] if p["side"] == "buy" else info["ask"]
            hit = None
            if p["side"] == "buy":
                if price <= p["sl"]:
                    hit, exit_price = "sl", p["sl"]
                elif price >= p["tp"]:
                    hit, exit_price = "tp", p["tp"]
            else:
                if price >= p["sl"]:
                    hit, exit_price = "sl", p["sl"]
                elif price <= p["tp"]:
                    hit, exit_price = "tp", p["tp"]
            if not hit:
                still_open.append(p)
                continue
            closed = dict(p)
            closed["price_close"] = exit_price
            closed["close_time"] = int(time.time())
            closed["result"] = hit
            closed["profit"] = _paper_profit(p, info, exit_price)
            with self.lock:
                self.paper_closed.append(closed)
                self.counters["realised"] += closed["profit"]
            self._event("close", "paper %s on %s closed at %s: %+.2f"
                        % (p["side"], p["symbol"], hit, closed["profit"]),
                        symbol=p["symbol"], profit=closed["profit"])
        with self.lock:
            self.paper_open = still_open
        self._save()

    def _roll_day(self):
        today = _today()
        if today != self.day:
            self.day = today
            self.counters = {"trades": 0, "realised": 0.0}
            if self.halted_reason == "daily_loss_limit_reached":
                self.halted_reason = ""
            self._save()

    def _halt(self, reason):
        with self.lock:
            self.halted_reason = reason
        self._event("halt", reason)
        self.stop(reason)


# --------------------------------------------------------------------------

def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _clamp(cfg):
    cfg["min_confidence"] = max(40, min(100, cfg["min_confidence"]))
    cfg["risk_percent"] = max(0.05, min(5.0, cfg["risk_percent"]))
    cfg["max_open"] = max(1, min(10, cfg["max_open"]))
    cfg["max_daily_trades"] = max(1, min(50, cfg["max_daily_trades"]))
    cfg["daily_loss_percent"] = max(0.5, min(25.0, cfg["daily_loss_percent"]))
    cfg["cooldown_minutes"] = max(0, min(1440, cfg["cooldown_minutes"]))
    cfg["interval_seconds"] = max(5, min(3600, cfg["interval_seconds"]))
    cfg["sl_atr"] = max(0.3, min(10.0, cfg["sl_atr"]))
    cfg["tp_atr"] = max(0.3, min(20.0, cfg["tp_atr"]))


def _paper_profit(p, info, exit_price=None):
    price = exit_price
    if price is None:
        price = info["bid"] if p["side"] == "buy" else info["ask"]
    move = (price - p["price_open"]) if p["side"] == "buy" \
        else (p["price_open"] - price)
    tick_size = info["trade_tick_size"] or info["point"]
    if not tick_size:
        return 0.0
    return round(move / tick_size * info["trade_tick_value"] * p["volume"], 2)
