"""The automatic trader: a background loop around strategy.analyze().

Three things matter more than the signal logic:

  * It starts in **paper** mode. Signals are recorded and tracked against real
    prices, but no order reaches the broker until the mode is switched to
    "live" deliberately.
  * Every trade passes the risk manager first — size from a risk percentage, a
    mandatory stop loss, caps on open/daily trades, a consecutive-loss brake,
    and a daily loss limit that shuts the engine off for the rest of the day.
  * Open trades are managed, not abandoned: partial profit at 1R, stop to
    break-even, then an ATR trail. On a scalping profile this is what turns a
    mediocre win rate into a survivable one.

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
    "mode": "paper",              # paper | live
    "profile": "scalp",           # scalp | trend
    "symbols": ["XAUUSD"],
    "entry_tf": "M5",
    "trend_tf": "M15",
    "min_confidence": 72,

    # risk
    "risk_percent": 0.5,          # of balance, per trade
    "max_open": 1,
    "max_daily_trades": 5,
    "daily_loss_percent": 2.0,
    "max_consecutive_losses": 3,  # pause for the day after this many
    "cooldown_minutes": 15,       # per symbol, after a trade

    # entry shaping
    "sl_atr": 1.1,
    "tp_atr": 1.8,
    "max_spread_points": 45,      # hard cap in points; 0 disables
    "deviation": 15,              # max slippage, in points

    # trade management (in R = the initial risk distance)
    "partial_at_r": 1.0,
    "partial_fraction": 0.5,
    "break_even_at_r": 1.0,
    "trail_after_r": 1.3,
    "trail_atr": 1.0,

    # when to trade, UTC. [from_h, from_m, to_h, to_m]
    "sessions": [[7, 0, 20, 30]],
    "blackouts": [[20, 45, 23, 59]],
    "trade_weekend": False,

    "interval_seconds": 10,
}

MAX_LOG = 400


class AutoTrader(object):
    def __init__(self, bridge):
        self.bridge = bridge
        self.lock = threading.RLock()
        self.running = False
        self.halted_reason = ""
        self.config = dict(DEFAULT_CONFIG)
        self.log = []
        self.scan = {}
        self.paper_open = []
        self.paper_closed = []
        self.managed = {}            # live ticket -> management record
        self.day = _today()
        self.counters = {"trades": 0, "realised": 0.0, "streak": 0}
        self.last_trade_at = {}
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
        self.paper_closed = d.get("paper_closed", [])[-800:]
        self.managed = d.get("managed", {})
        self.last_trade_at = d.get("last_trade_at", {})
        self.day = d.get("day", _today())
        self.counters = d.get("counters", {"trades": 0, "realised": 0.0,
                                           "streak": 0})
        self.counters.setdefault("streak", 0)
        self.halted_reason = d.get("halted_reason", "")
        self._roll_day()

    def _save(self):
        tmp = STATE_PATH + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({
                    "config": self.config, "log": self.log[-MAX_LOG:],
                    "paper_open": self.paper_open,
                    "paper_closed": self.paper_closed[-800:],
                    "managed": self.managed,
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
        self._event("start", "engine started in %s mode (%s profile, %s)"
                    % (self.config["mode"], self.config["profile"],
                       ", ".join(self._symbols())))
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
            if "profile" in (updates or {}):
                name = str(updates["profile"])
                if name not in strategy.PROFILES:
                    raise ValueError("profile must be scalp or trend")
                if name != self.config["profile"]:
                    prof = strategy.profile(name)
                    self.config["profile"] = name
                    for key in ("entry_tf", "trend_tf", "min_confidence",
                                "sl_atr", "tp_atr"):
                        self.config[key] = prof[key]
                    self._event("profile", "switched to the %s profile" % name)
            for k, v in (updates or {}).items():
                if k not in DEFAULT_CONFIG or k == "profile":
                    continue
                if k == "mode":
                    if v not in ("paper", "live"):
                        raise ValueError("mode must be paper or live")
                    if v != self.config["mode"]:
                        self._event("mode", "mode changed to %s" % v)
                elif k == "symbols":
                    v = [str(x).strip() for x in (v or []) if str(x).strip()][:12]
                elif k in ("sessions", "blackouts"):
                    v = _clean_windows(v)
                elif k == "trade_weekend":
                    v = bool(v)
                elif isinstance(DEFAULT_CONFIG[k], bool):
                    v = bool(v)
                elif isinstance(DEFAULT_CONFIG[k], int):
                    v = int(float(v))
                elif isinstance(DEFAULT_CONFIG[k], float):
                    v = float(v)
                self.config[k] = v
            _clamp(self.config)
            self._save()
        return self.status()

    def clear_halt(self):
        with self.lock:
            self.halted_reason = ""
            self.counters["streak"] = 0
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
                "profiles": sorted(strategy.PROFILES.keys()),
                "day": self.day,
                "counters": dict(self.counters),
                "floating": floating,
                "paper_open": paper,
                "paper_closed": self.paper_closed[-40:],
                "paper_stats": _stats(self.paper_closed),
                "scan": dict(self.scan),
                "log": self.log[-60:],
                "last_cycle": self.last_cycle,
                "cycle_error": self.cycle_error,
                "session_open": strategy.session_state(
                    time.time(), self.config["sessions"],
                    self.config["blackouts"],
                    self.config["trade_weekend"]) is None,
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
        self._manage_open_trades()

        if self.halted_reason:
            self.stop(self.halted_reason)
            return

        account = self.bridge.account()
        limit = account["balance"] * self.config["daily_loss_percent"] / 100.0
        if limit > 0 and self.counters["realised"] <= -limit:
            self._halt("daily_loss_limit_reached")
            return
        if self.counters["streak"] >= self.config["max_consecutive_losses"]:
            self._halt("consecutive_loss_limit_reached")
            return
        if self.counters["trades"] >= self.config["max_daily_trades"]:
            return
        if len(self._bot_positions()) >= self.config["max_open"]:
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
            if not decision.get("side") or self._blocked_by_risk(sym):
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

    def _strategy_cfg(self):
        c = self.config
        return {
            "mode_profile": c["profile"],
            "min_confidence": c["min_confidence"],
            "sl_atr": c["sl_atr"],
            "tp_atr": c["tp_atr"],
            "sessions": c["sessions"],
            "blackouts": c["blackouts"],
            "trade_weekend": c["trade_weekend"],
        }

    def _study(self, sym):
        info = self.bridge.symbol_info(sym)
        entry = self.bridge.candles(sym, self.config["entry_tf"], 260)
        trend = self.bridge.candles(sym, self.config["trend_tf"], 260)
        spread = max(0.0, info["ask"] - info["bid"])
        d = strategy.analyze(entry, trend, sym, spread_price=spread,
                             cfg=self._strategy_cfg(), now_ts=time.time())
        cap = self.config["max_spread_points"]
        if d.get("side") and cap and info["point"] and \
                spread / info["point"] > cap:
            d["side"] = None
            d["blockers"].append("spread_over_hard_cap")
        d["time"] = int(time.time())
        d["digits"] = info["digits"]
        d["spread_points"] = round(spread / info["point"]) if info["point"] else 0
        self.scan[sym] = d
        return d

    def _bot_positions(self):
        if self.config["mode"] == "paper":
            return list(self.paper_open)
        try:
            return [p for p in self.bridge.positions()
                    if str(p.get("comment", "")).startswith("bot")]
        except Exception:
            return []

    def _blocked_by_risk(self, sym):
        now = time.time()
        if now - self.last_trade_at.get(sym, 0) < self.config["cooldown_minutes"] * 60:
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
        info = self.bridge.symbol_info(sym)      # fresh quote, not the scan's
        account = self.bridge.account()
        side = d["side"]

        spread = max(0.0, info["ask"] - info["bid"])
        cap = self.config["max_spread_points"]
        if cap and info["point"] and spread / info["point"] > cap:
            self._event("skip", "spread widened to %d points on %s, standing down"
                        % (spread / info["point"], sym), symbol=sym)
            return

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
            self._event("skip", "risk budget below the minimum lot on %s" % sym,
                        symbol=sym)
            return
        if calc["estimated_loss"] > risk_amount * 1.5:
            self._event("skip",
                        "minimum lot on %s would risk %.2f against a budget of %.2f"
                        % (sym, calc["estimated_loss"], risk_amount), symbol=sym)
            return

        sl = entry - d["sl_points"] if side == "buy" else entry + d["sl_points"]
        tp = entry + d["tp_points"] if side == "buy" else entry - d["tp_points"]
        sl, tp = round(sl, info["digits"]), round(tp, info["digits"])

        record = {
            "symbol": sym, "side": side, "volume": lot, "opened_volume": lot,
            "price_open": entry, "sl": sl, "tp": tp, "initial_sl": sl,
            "confidence": d["confidence"], "reasons": d["reasons"],
            "time": int(time.time()), "digits": info["digits"],
            "risk": calc["estimated_loss"], "mode": self.config["mode"],
            "atr": d["atr"], "rr": d.get("rr"),
            "be_done": False, "partial_done": False, "booked": 0.0,
        }

        if self.config["mode"] == "paper":
            with self.lock:
                self.paper_open.append(record)
        else:
            try:
                res = self.bridge.market_order(
                    symbol=sym, side=side, volume=lot, sl=sl, tp=tp,
                    deviation=self.config["deviation"],
                    comment="bot%d" % d["confidence"])
            except Exception as exc:
                self._event("error", "order rejected on %s: %s" % (sym, exc),
                            symbol=sym)
                return
            record["ticket"] = res.get("order")
            record["price_open"] = res.get("price") or entry
            with self.lock:
                self.managed[str(record["ticket"])] = record

        with self.lock:
            self.counters["trades"] += 1
            self.last_trade_at[sym] = time.time()
        self._event("trade", "%s %s %.2f lots at %.*f — confidence %d%%, "
                             "risk %.2f, target %.1fR"
                    % (side, sym, lot, info["digits"], record["price_open"],
                       d["confidence"], calc["estimated_loss"], d.get("rr") or 0),
                    symbol=sym, side=side, confidence=d["confidence"],
                    volume=lot, sl=sl, tp=tp, mode=self.config["mode"],
                    reasons=d["reasons"])
        self._save()

    # ------------------------------------------------------- trade management
    def _manage_open_trades(self):
        """Partial profit at 1R, stop to break-even, then trail."""
        c = self.config
        if c["mode"] == "paper":
            targets = list(self.paper_open)
        else:
            live = {str(p["ticket"]): p for p in self._bot_positions()}
            for ticket in list(self.managed):
                if ticket not in live:
                    self.managed.pop(ticket, None)    # closed by SL/TP
            targets = []
            for ticket, pos in live.items():
                rec = self.managed.get(ticket)
                if rec:
                    rec["volume"] = pos["volume"]
                    rec["sl"] = pos["sl"]
                    targets.append(rec)

        for rec in targets:
            try:
                info = self.bridge.symbol_info(rec["symbol"])
            except Exception:
                continue
            price = info["bid"] if rec["side"] == "buy" else info["ask"]
            risk = abs(rec["price_open"] - rec["initial_sl"])
            if risk <= 0:
                continue
            moved = (price - rec["price_open"]) if rec["side"] == "buy" \
                else (rec["price_open"] - price)
            r = moved / risk

            # 1. partial profit
            if not rec["partial_done"] and c["partial_fraction"] > 0 \
                    and r >= c["partial_at_r"]:
                part = round(rec["volume"] * c["partial_fraction"], 2)
                if part >= info["volume_min"] - 1e-9 and part < rec["volume"]:
                    if self._reduce(rec, part, price, info):
                        rec["partial_done"] = True
                        self._event("manage", "took %.2f lots off %s at %.1fR"
                                    % (part, rec["symbol"], r), symbol=rec["symbol"])
                else:
                    rec["partial_done"] = True    # too small to split

            # 2. break-even
            new_sl = None
            if not rec["be_done"] and r >= c["break_even_at_r"]:
                buffer = info["point"] * 2
                be = rec["price_open"] + buffer if rec["side"] == "buy" \
                    else rec["price_open"] - buffer
                if _is_better_stop(rec["side"], be, rec["sl"]):
                    new_sl = be
                rec["be_done"] = True

            # 3. ATR trail
            if r >= c["trail_after_r"] and rec.get("atr"):
                dist = rec["atr"] * c["trail_atr"]
                trail = price - dist if rec["side"] == "buy" else price + dist
                if _is_better_stop(rec["side"], trail, new_sl or rec["sl"]):
                    new_sl = trail

            if new_sl is not None:
                new_sl = round(new_sl, info["digits"])
                if self._move_stop(rec, new_sl):
                    rec["sl"] = new_sl
                    self._event("manage", "stop on %s moved to %.*f (%.1fR)"
                                % (rec["symbol"], info["digits"], new_sl, r),
                                symbol=rec["symbol"])
        self._save()

    def _reduce(self, rec, part, price, info):
        if self.config["mode"] == "paper":
            booked = _paper_profit(dict(rec, volume=part), info, price)
            with self.lock:
                rec["volume"] = round(rec["volume"] - part, 2)
                rec["booked"] = rec.get("booked", 0.0) + booked
                self.counters["realised"] += booked
                self.paper_closed.append(dict(
                    rec, volume=part, price_close=price,
                    close_time=int(time.time()), result="partial",
                    profit=booked))
            return True
        try:
            self.bridge.close_position(rec["ticket"], volume=part)
            return True
        except Exception as exc:
            self._event("error", "partial close failed on %s: %s"
                        % (rec["symbol"], exc), symbol=rec["symbol"])
            return False

    def _move_stop(self, rec, new_sl):
        if self.config["mode"] == "paper":
            return True
        try:
            self.bridge.modify_position(rec["ticket"], sl=new_sl, tp=rec["tp"])
            return True
        except Exception as exc:
            self._event("error", "could not move the stop on %s: %s"
                        % (rec["symbol"], exc), symbol=rec["symbol"])
            return False

    # --------------------------------------------------------------- paper
    def _update_paper_positions(self):
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
            hit = exit_price = None
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
                total = closed["profit"] + p.get("booked", 0.0)
                self.counters["streak"] = 0 if total > 0 \
                    else self.counters["streak"] + 1
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
            self.counters = {"trades": 0, "realised": 0.0, "streak": 0}
            if self.halted_reason in ("daily_loss_limit_reached",
                                      "consecutive_loss_limit_reached"):
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


def _is_better_stop(side, candidate, current):
    if not current:
        return True
    return candidate > current if side == "buy" else candidate < current


def _clean_windows(windows):
    out = []
    for w in (windows or [])[:8]:
        try:
            a, b, c, d = [int(x) for x in w[:4]]
        except (TypeError, ValueError):
            continue
        out.append([max(0, min(23, a)), max(0, min(59, b)),
                    max(0, min(23, c)), max(0, min(59, d))])
    return out


def _clamp(cfg):
    cfg["min_confidence"] = max(40, min(100, cfg["min_confidence"]))
    cfg["risk_percent"] = max(0.05, min(5.0, cfg["risk_percent"]))
    cfg["max_open"] = max(1, min(10, cfg["max_open"]))
    cfg["max_daily_trades"] = max(1, min(50, cfg["max_daily_trades"]))
    cfg["daily_loss_percent"] = max(0.5, min(25.0, cfg["daily_loss_percent"]))
    cfg["max_consecutive_losses"] = max(1, min(20, cfg["max_consecutive_losses"]))
    cfg["cooldown_minutes"] = max(0, min(1440, cfg["cooldown_minutes"]))
    cfg["interval_seconds"] = max(5, min(3600, cfg["interval_seconds"]))
    cfg["sl_atr"] = max(0.3, min(10.0, cfg["sl_atr"]))
    cfg["tp_atr"] = max(0.3, min(20.0, cfg["tp_atr"]))
    cfg["max_spread_points"] = max(0, min(10000, cfg["max_spread_points"]))
    cfg["deviation"] = max(0, min(500, cfg["deviation"]))
    cfg["partial_at_r"] = max(0.2, min(10.0, cfg["partial_at_r"]))
    cfg["partial_fraction"] = max(0.0, min(0.9, cfg["partial_fraction"]))
    cfg["break_even_at_r"] = max(0.2, min(10.0, cfg["break_even_at_r"]))
    cfg["trail_after_r"] = max(0.2, min(20.0, cfg["trail_after_r"]))
    cfg["trail_atr"] = max(0.2, min(10.0, cfg["trail_atr"]))


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


def _stats(closed):
    if not closed:
        return {"count": 0, "net": 0.0, "win_rate": 0.0, "profit_factor": 0.0,
                "best": 0.0, "worst": 0.0, "max_drawdown": 0.0}
    nets = [d["profit"] for d in closed]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    equity = peak = dd = 0.0
    for x in nets:
        equity += x
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {
        "count": len(nets), "net": round(sum(nets), 2),
        "win_rate": round(len(wins) / len(nets) * 100.0, 1),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else 0.0,
        "best": round(max(nets), 2), "worst": round(min(nets), 2),
        "max_drawdown": round(dd, 2),
    }
