"""Signal engine: reads candles, returns a decision with a confidence score.

Deliberately transparent — every decision carries the list of checks that
passed and failed, so the panel can show *why* a trade was taken or skipped.
No machine learning, no fitted parameters: a confluence of classic trend,
momentum and volatility filters, each of which either agrees or it does not.

Nothing here places orders; autotrader.py decides what to do with a signal.
"""

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


def atr(candles, period=14):
    """Average true range series. Positions before `period` are None."""
    if len(candles) <= period:
        return [None] * len(candles)
    trs = [candles[0]["h"] - candles[0]["l"]]
    for i in range(1, len(candles)):
        c = candles[i]
        prev_close = candles[i - 1]["c"]
        trs.append(max(c["h"] - c["l"],
                       abs(c["h"] - prev_close),
                       abs(c["l"] - prev_close)))
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


def slope(series, lookback=3):
    """Average change per bar over the last `lookback` bars."""
    if len(series) <= lookback:
        return 0.0
    return (series[-1] - series[-1 - lookback]) / float(lookback)


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------
# Each check returns (agrees, weight, label). Weights add up to 100 so the
# confidence score reads as a percentage of the evidence that lined up.

DEFAULTS = {
    "entry_tf": "M15",
    "trend_tf": "H1",
    "min_confidence": 70,
    "atr_period": 14,
    "sl_atr": 1.5,          # stop loss = 1.5 x ATR
    "tp_atr": 2.5,          # take profit = 2.5 x ATR  (reward:risk ≈ 1.67)
    "max_spread_atr": 0.15,  # skip when the spread eats >15% of one ATR
    "rsi_long": [45, 72],   # acceptable RSI band for a long
    "rsi_short": [28, 55],
}


def analyze(entry_candles, trend_candles, symbol, spread_price=0.0, cfg=None):
    """Study one symbol and return a decision dict.

    entry_candles / trend_candles: lists of {t,o,h,l,c,v}, oldest first.
    spread_price: current ask-bid, in price units.
    """
    C = dict(DEFAULTS)
    if cfg:
        C.update({k: v for k, v in cfg.items() if k in DEFAULTS})

    result = {
        "symbol": symbol, "side": None, "confidence": 0,
        "reasons": [], "blockers": [], "atr": None,
        "sl_points": None, "tp_points": None, "price": None,
    }

    if len(entry_candles) < 60 or len(trend_candles) < 60:
        result["blockers"].append("not_enough_history")
        return result

    # the newest candle is still forming; judge on closed ones
    ec = entry_candles[:-1]
    tc = trend_candles[:-1]
    closes = [c["c"] for c in ec]
    tcloses = [c["c"] for c in tc]
    price = entry_candles[-1]["c"]
    result["price"] = price

    atr_series = atr(ec, C["atr_period"])
    a = atr_series[-1] if atr_series else None
    if not a or a <= 0:
        result["blockers"].append("no_volatility_reading")
        return result
    result["atr"] = a

    # -- gate 1: is this market even tradable right now? -------------------
    if spread_price and spread_price > a * C["max_spread_atr"]:
        result["blockers"].append("spread_too_wide")
        return result

    recent_atr = [x for x in atr_series[-30:] if x]
    if recent_atr and a < (sum(recent_atr) / len(recent_atr)) * 0.5:
        result["blockers"].append("market_too_quiet")
        return result

    # -- gate 2: higher timeframe direction --------------------------------
    t_fast, t_slow = ema(tcloses, 50), ema(tcloses, 200)
    if t_fast[-1] > t_slow[-1] and tcloses[-1] > t_slow[-1]:
        bias = "buy"
    elif t_fast[-1] < t_slow[-1] and tcloses[-1] < t_slow[-1]:
        bias = "sell"
    else:
        result["blockers"].append("higher_timeframe_undecided")
        return result

    long_side = bias == "buy"

    # -- the weighted checks ----------------------------------------------
    e20, e50 = ema(closes, 20), ema(closes, 50)
    r = rsi(closes, 14)
    _, _, hist = macd(closes)
    checks = []

    # trend agreement on the entry timeframe (25)
    checks.append((
        (e20[-1] > e50[-1]) if long_side else (e20[-1] < e50[-1]),
        25, "entry_trend_aligned"))

    # price on the right side of the fast average (15)
    checks.append((
        (price > e20[-1]) if long_side else (price < e20[-1]),
        15, "price_with_trend"))

    # momentum has turned our way and is still building (20)
    checks.append((
        (hist[-1] > 0 and hist[-1] > hist[-2]) if long_side
        else (hist[-1] < 0 and hist[-1] < hist[-2]),
        20, "momentum_building"))

    # RSI in the healthy band — trending, not yet exhausted (20)
    band = C["rsi_long"] if long_side else C["rsi_short"]
    rv = r[-1]
    checks.append((rv is not None and band[0] <= rv <= band[1],
                   20, "rsi_in_band"))

    # the moving average itself is sloping our way (10)
    sl20 = slope(e20, 3)
    checks.append(((sl20 > 0) if long_side else (sl20 < 0),
                   10, "moving_average_turning"))

    # entering after a pullback, not after an extended run (10)
    dist = abs(price - e20[-1]) / a
    checks.append((dist <= 1.2, 10, "not_overextended"))

    score = 0
    for agrees, weight, label in checks:
        if agrees:
            score += weight
            result["reasons"].append(label)
        else:
            result["blockers"].append(label)

    result["confidence"] = score
    if score >= C["min_confidence"]:
        result["side"] = bias
        result["sl_points"] = a * C["sl_atr"]
        result["tp_points"] = a * C["tp_atr"]
    return result
