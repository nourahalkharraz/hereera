"""Signal engine: reads candles, returns a decision with a confidence score.

Two profiles:

  scalp  — fast entries on a low timeframe (M5 by default) inside the M15/H1
           trend. Tuned for XAUUSD, where the spread is the single biggest
           reason a technically-correct trade still loses money.
  trend  — the slower M15/H1 profile.

Deliberately transparent: every decision carries the checks that passed and the
ones that failed, so the panel can show *why* a trade was taken or skipped.
No fitted parameters and no machine learning — a confluence of classic trend,
momentum, volatility and cost filters, each of which either agrees or it does
not. Nothing here places orders; autotrader.py decides what to do with a
signal, and backtest.py replays it over history.
"""

import time as _time

# --------------------------------------------------------------------------
# indicators (plain python — no numpy needed)
# --------------------------------------------------------------------------

def ema(values, period):
    """Exponential moving average series, same length as `values`."""
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def rsi(values, period=14):
    """Wilder's RSI. Positions before `period` are None."""
    if len(values) <= period:
        return [None] * len(values)
    out = [None] * period
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out.append(100.0 if avg_loss == 0 else
               100.0 - 100.0 / (1 + avg_gain / avg_loss))
    for i in range(period + 1, len(values)):
        d = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period
        out.append(100.0 if avg_loss == 0 else
                   100.0 - 100.0 / (1 + avg_gain / avg_loss))
    return out


def true_ranges(candles):
    trs = [candles[0]["h"] - candles[0]["l"]]
    for i in range(1, len(candles)):
        c = candles[i]
        pc = candles[i - 1]["c"]
        trs.append(max(c["h"] - c["l"], abs(c["h"] - pc), abs(c["l"] - pc)))
    return trs


def atr(candles, period=14):
    """Average true range series. Positions before `period` are None."""
    if len(candles) <= period:
        return [None] * len(candles)
    trs = true_ranges(candles)
    out = [None] * (period - 1)
    val = sum(trs[:period]) / period
    out.append(val)
    for i in range(period, len(trs)):
        val = (val * (period - 1) + trs[i]) / period
        out.append(val)
    return out


def macd(values, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram)."""
    ef, es = ema(values, fast), ema(values, slow)
    line = [a - b for a, b in zip(ef, es)]
    sig = ema(line, signal)
    hist = [a - b for a, b in zip(line, sig)]
    return line, sig, hist


def adx(candles, period=14):
    """Wilder's ADX with the directional indicators.

    Returns (adx, plus_di, minus_di) as the latest values, or (0, 0, 0) when
    there is not enough history. ADX answers "is there a trend at all?", which
    keeps the engine out of the chop where scalping bleeds.
    """
    n = len(candles)
    if n < period * 2 + 2:
        return 0.0, 0.0, 0.0
    plus_dm, minus_dm = [], []
    for i in range(1, n):
        up = candles[i]["h"] - candles[i - 1]["h"]
        down = candles[i - 1]["l"] - candles[i]["l"]
        plus_dm.append(up if (up > down and up > 0) else 0.0)
        minus_dm.append(down if (down > up and down > 0) else 0.0)
    trs = true_ranges(candles)[1:]

    def wilder(seq):
        out = [sum(seq[:period])]
        for i in range(period, len(seq)):
            out.append(out[-1] - out[-1] / period + seq[i])
        return out

    tr_s, p_s, m_s = wilder(trs), wilder(plus_dm), wilder(minus_dm)
    dxs = []
    for i in range(len(tr_s)):
        if tr_s[i] == 0:
            dxs.append(0.0)
            continue
        pdi = 100.0 * p_s[i] / tr_s[i]
        mdi = 100.0 * m_s[i] / tr_s[i]
        denom = pdi + mdi
        dxs.append(100.0 * abs(pdi - mdi) / denom if denom else 0.0)
    if len(dxs) < period:
        return 0.0, 0.0, 0.0
    adx_val = sum(dxs[:period]) / period
    for i in range(period, len(dxs)):
        adx_val = (adx_val * (period - 1) + dxs[i]) / period
    last_tr = tr_s[-1] or 1e-9
    return adx_val, 100.0 * p_s[-1] / last_tr, 100.0 * m_s[-1] / last_tr


def slope(series, lookback=3):
    """Average change per bar over the last `lookback` bars."""
    if len(series) <= lookback:
        return 0.0
    return (series[-1] - series[-1 - lookback]) / float(lookback)


def body_ratio(candle):
    rng = candle["h"] - candle["l"]
    return abs(candle["c"] - candle["o"]) / rng if rng else 0.0


# --------------------------------------------------------------------------
# profiles
# --------------------------------------------------------------------------
# Weights add up to 100, so the confidence score reads as "how much of the
# evidence lined up".

PROFILES = {
    "scalp": {
        "entry_tf": "M5",
        "trend_tf": "M15",
        "min_confidence": 72,
        "atr_period": 14,
        "sl_atr": 1.1,
        "tp_atr": 1.8,
        "structure_lookback": 12,   # swing high/low used to place the stop
        "sl_min_atr": 0.7,
        "sl_max_atr": 1.6,
        "min_rr": 1.5,
        "max_spread_atr": 0.25,     # spread must stay small next to one ATR
        "min_tp_spread": 5.0,       # target must be at least 5x the spread
        "adx_min": 20.0,
        "atr_regime": [0.65, 2.2],  # vs the 50-bar average ATR
        "rsi_long": [48, 74],
        "rsi_short": [26, 52],
        "max_extension_atr": 1.0,
        "trend_ema": [21, 55],      # faster pair for the trend timeframe
        "weights": {
            "trend_aligned": 18, "price_with_trend": 12, "momentum": 16,
            "rsi_band": 12, "ma_turning": 8, "not_overextended": 10,
            "adx_strong": 14, "candle_confirms": 10,
        },
    },
    "trend": {
        "entry_tf": "M15",
        "trend_tf": "H1",
        "min_confidence": 70,
        "atr_period": 14,
        "sl_atr": 1.5,
        "tp_atr": 2.5,
        "structure_lookback": 16,
        "sl_min_atr": 0.8,
        "sl_max_atr": 2.5,
        "min_rr": 1.6,
        "max_spread_atr": 0.20,
        "min_tp_spread": 4.0,
        "adx_min": 18.0,
        "atr_regime": [0.5, 2.5],
        "rsi_long": [45, 72],
        "rsi_short": [28, 55],
        "max_extension_atr": 1.2,
        "trend_ema": [50, 200],
        "weights": {
            "trend_aligned": 22, "price_with_trend": 13, "momentum": 17,
            "rsi_band": 15, "ma_turning": 9, "not_overextended": 10,
            "adx_strong": 8, "candle_confirms": 6,
        },
    },
}

DEFAULTS = dict(PROFILES["scalp"])

# Trading sessions in UTC. Gold barely moves in the Asian session and the
# spread widens around the broker's rollover, so both are skipped by default.
DEFAULT_SESSIONS = [[7, 0, 20, 30]]     # [from_h, from_m, to_h, to_m]
DEFAULT_BLACKOUTS = [[20, 45, 23, 59]]  # rollover / thin liquidity


def profile(name):
    return dict(PROFILES.get(name, PROFILES["scalp"]))


# --------------------------------------------------------------------------
# time filters
# --------------------------------------------------------------------------

def _minutes(ts):
    tm = _time.gmtime(ts)
    return tm.tm_hour * 60 + tm.tm_min, tm.tm_wday


def in_windows(ts, windows):
    mins, _ = _minutes(ts)
    for w in windows or []:
        start = w[0] * 60 + w[1]
        end = w[2] * 60 + w[3]
        if start <= end:
            if start <= mins <= end:
                return True
        elif mins >= start or mins <= end:   # window wraps past midnight
            return True
    return False


def session_state(ts, sessions, blackouts, trade_weekend=False):
    """Returns None when trading is allowed, otherwise the blocking reason."""
    mins, wday = _minutes(ts)          # Monday is 0, Sunday is 6
    if not trade_weekend:
        if wday == 5:                                  # Saturday: closed
            return "market_closed_weekend"
        if wday == 6 and mins < 22 * 60:               # Sunday before the open
            return "market_closed_weekend"
        if wday == 4 and mins > 21 * 60:               # after the Friday close
            return "market_closed_weekend"
    if blackouts and in_windows(ts, blackouts):
        return "blackout_window"
    if sessions and not in_windows(ts, sessions):
        return "outside_session"
    return None


# --------------------------------------------------------------------------
# the analysis
# --------------------------------------------------------------------------

def analyze(entry_candles, trend_candles, symbol, spread_price=0.0,
            cfg=None, now_ts=None):
    """Study one symbol and return a decision dict.

    entry_candles / trend_candles: lists of {t,o,h,l,c,v}, oldest first, the
    last one still forming. spread_price: current ask-bid in price units.
    """
    C = profile((cfg or {}).get("mode_profile", "scalp"))
    if cfg:
        # profile keys can be overridden, and these have no profile default
        C.update({k: v for k, v in cfg.items() if k in C})
        for key in ("sessions", "blackouts", "trade_weekend"):
            if key in cfg and cfg[key] is not None:
                C[key] = cfg[key]

    result = {
        "symbol": symbol, "side": None, "confidence": 0,
        "reasons": [], "blockers": [], "atr": None,
        "sl_points": None, "tp_points": None, "price": None,
        "adx": None, "rr": None,
    }

    if len(entry_candles) < 60 or len(trend_candles) < 60:
        result["blockers"].append("not_enough_history")
        return result

    ec = entry_candles[:-1]          # judge on closed candles only
    tc = trend_candles[:-1]
    closes = [c["c"] for c in ec]
    tcloses = [c["c"] for c in tc]
    price = entry_candles[-1]["c"]
    result["price"] = price
    ts = now_ts if now_ts is not None else entry_candles[-1]["t"]

    # -- gate 0: are we inside a session we want to trade? -----------------
    blocked = session_state(ts, C.get("sessions", DEFAULT_SESSIONS),
                            C.get("blackouts", DEFAULT_BLACKOUTS),
                            C.get("trade_weekend", False))
    if blocked:
        result["blockers"].append(blocked)
        return result

    atr_series = atr(ec, C["atr_period"])
    a = atr_series[-1] if atr_series else None
    if not a or a <= 0:
        result["blockers"].append("no_volatility_reading")
        return result
    result["atr"] = a

    # -- gate 1: cost. On gold this rejects more trades than anything else -
    if spread_price:
        if spread_price > a * C["max_spread_atr"]:
            result["blockers"].append("spread_too_wide")
            return result
        if a * C["tp_atr"] < spread_price * C["min_tp_spread"]:
            result["blockers"].append("target_too_small_for_spread")
            return result

    # -- gate 2: volatility regime. Too quiet drifts, too wild is news ----
    recent = [x for x in atr_series[-50:] if x]
    if recent:
        avg = sum(recent) / len(recent)
        lo, hi = C["atr_regime"]
        if a < avg * lo:
            result["blockers"].append("market_too_quiet")
            return result
        if a > avg * hi:
            result["blockers"].append("volatility_spike")   # likely news
            return result

    # -- gate 3: higher timeframe direction --------------------------------
    fast_p, slow_p = C["trend_ema"]
    t_fast, t_slow = ema(tcloses, fast_p), ema(tcloses, slow_p)
    if t_fast[-1] > t_slow[-1] and tcloses[-1] > t_slow[-1]:
        bias = "buy"
    elif t_fast[-1] < t_slow[-1] and tcloses[-1] < t_slow[-1]:
        bias = "sell"
    else:
        result["blockers"].append("higher_timeframe_undecided")
        return result
    long_side = bias == "buy"

    # -- the weighted checks ----------------------------------------------
    W = C["weights"]
    e20, e50 = ema(closes, 20), ema(closes, 50)
    r = rsi(closes, 14)
    _, _, hist = macd(closes)
    adx_val, pdi, mdi = adx(ec, 14)
    result["adx"] = round(adx_val, 1)
    last = ec[-1]
    checks = []

    checks.append(((e20[-1] > e50[-1]) if long_side else (e20[-1] < e50[-1]),
                   W["trend_aligned"], "entry_trend_aligned"))

    checks.append(((price > e20[-1]) if long_side else (price < e20[-1]),
                   W["price_with_trend"], "price_with_trend"))

    checks.append(((hist[-1] > 0 and hist[-1] > hist[-2]) if long_side
                   else (hist[-1] < 0 and hist[-1] < hist[-2]),
                   W["momentum"], "momentum_building"))

    band = C["rsi_long"] if long_side else C["rsi_short"]
    rv = r[-1]
    checks.append((rv is not None and band[0] <= rv <= band[1],
                   W["rsi_band"], "rsi_in_band"))

    sl20 = slope(e20, 3)
    checks.append(((sl20 > 0) if long_side else (sl20 < 0),
                   W["ma_turning"], "moving_average_turning"))

    extension = abs(price - e20[-1]) / a
    checks.append((extension <= C["max_extension_atr"],
                   W["not_overextended"], "not_overextended"))

    # a real trend, and the directional index agrees with our side
    directional = (pdi > mdi) if long_side else (mdi > pdi)
    checks.append((adx_val >= C["adx_min"] and directional,
                   W["adx_strong"], "trend_strength"))

    # the last closed candle should point our way with a real body
    closed_our_way = (last["c"] > last["o"]) if long_side else (last["c"] < last["o"])
    checks.append((closed_our_way and body_ratio(last) >= 0.4,
                   W["candle_confirms"], "candle_confirms"))

    score = 0
    for agrees, weight, label in checks:
        if agrees:
            score += weight
            result["reasons"].append(label)
        else:
            result["blockers"].append(label)

    result["confidence"] = int(round(score))
    if score < C["min_confidence"]:
        return result

    # -- stop and target ---------------------------------------------------
    # Prefer the recent swing: a stop just past structure is harder for noise
    # to reach than a fixed multiple, but it is clamped so one wide bar cannot
    # blow the risk budget out.
    look = min(C["structure_lookback"], len(ec))
    window = ec[-look:]
    if long_side:
        struct = min(c["l"] for c in window)
        sl_dist = price - struct + a * 0.15
    else:
        struct = max(c["h"] for c in window)
        sl_dist = struct - price + a * 0.15
    sl_dist = max(a * C["sl_min_atr"], min(a * C["sl_max_atr"], sl_dist))
    # The target follows the risk actually taken: a structure stop that ends up
    # wider than the ATR default must earn a proportionally wider target, or
    # the trade is not worth taking.
    tp_dist = max(a * C["tp_atr"], sl_dist * C.get("min_rr", 1.5))

    # keep the reward worth the risk after costs
    if spread_price and tp_dist < spread_price * C["min_tp_spread"]:
        result["blockers"].append("target_too_small_for_spread")
        return result
    rr = tp_dist / sl_dist if sl_dist else 0
    if rr < C.get("min_rr", 1.2):
        result["blockers"].append("reward_below_risk")
        return result

    result["side"] = bias
    result["sl_points"] = sl_dist
    result["tp_points"] = tp_dist
    result["rr"] = round(rr, 2)
    return result
