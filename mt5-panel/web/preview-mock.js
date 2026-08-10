/* Offline preview: the panel with a simulated market, no server behind it.

   Intercepts fetch("/api/…") and answers from a random-walk market held in
   memory, so the interface can be opened anywhere — a phone at work, say —
   without the PC or MetaTrader running. The signal engine below is a direct
   translation of strategy.py, so the Auto tab shows real scoring on fake
   prices rather than invented output. Nothing here reaches a broker.

   Only loaded by preview.html. The real panel never includes this file. */

(function () {
  "use strict";

  // ------------------------------------------------------------- market
  var SPECS = {
    XAUUSD: [2334.50, 2, 0.01, 25, 1.0, "Gold vs US Dollar"],
    EURUSD: [1.0865, 5, 0.00001, 12, 1.0, "Euro vs US Dollar"],
    GBPUSD: [1.2712, 5, 0.00001, 15, 1.0, "Great Britain Pound vs US Dollar"],
    USDJPY: [151.42, 3, 0.001, 14, 0.66, "US Dollar vs Japanese Yen"],
    BTCUSD: [64210.0, 2, 0.01, 900, 1.0, "Bitcoin vs US Dollar"],
  };
  var WATCH = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"];
  var TF_SECONDS = { M1: 60, M5: 300, M15: 900, M30: 1800, H1: 3600,
                     H4: 14400, D1: 86400, W1: 604800, MN1: 2592000 };

  var state = {};
  Object.keys(SPECS).forEach(function (name) {
    var s = SPECS[name];
    state[name] = { price: s[0], digits: s[1], point: s[2], spread: s[3],
                    tickValue: s[4], desc: s[5], last: Date.now() / 1000 };
  });

  var balance = 10000, ticket = 50000;
  var positions = [], orders = [], deals = [];

  function gauss() {
    var u = 0, v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  function round(v, d) { return Number(v.toFixed(d)); }

  function quote(name) {
    var st = state[name];
    var now = Date.now() / 1000;
    var dt = Math.max(0, now - st.last);
    st.last = now;
    st.price = Math.max(st.point * 10,
                        st.price + gauss() * st.price * 0.00004 * Math.sqrt(Math.max(dt, 0.2)));
    var half = st.spread * st.point / 2;
    return {
      symbol: name, description: st.desc, path: "Preview\\" + name,
      digits: st.digits, point: st.point,
      bid: round(st.price - half, st.digits), ask: round(st.price + half, st.digits),
      last: round(st.price, st.digits), spread: st.spread,
      volume_min: 0.01, volume_max: 100, volume_step: 0.01,
      trade_contract_size: 100, trade_tick_value: st.tickValue,
      trade_tick_size: st.point, stops_level: 0,
      visible: WATCH.indexOf(name) >= 0,
    };
  }

  // deterministic history per symbol+timeframe, so charts stay stable
  var candleCache = {};
  function candles(name, tf, count) {
    var step = TF_SECONDS[tf] || 900;
    var key = name + tf;
    var st = state[name];
    if (!candleCache[key]) {
      var seed = 0;
      for (var i = 0; i < key.length; i++) seed = (seed * 31 + key.charCodeAt(i)) >>> 0;
      var rnd = function () {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
      };
      var g = function () {
        return Math.sqrt(-2 * Math.log(rnd() || 1e-9)) * Math.cos(2 * Math.PI * rnd());
      };
      var bars = [];
      var price = st.price;
      var now = Math.floor(Date.now() / 1000 / step) * step;
      var drift = st.price * 0.0004;
      for (var k = 0; k < 400; k++) {
        var vol = price * 0.0022;
        var o = price;
        var c = price + g() * vol + (Math.sin(k / 40) * drift);
        var h = Math.max(o, c) + Math.abs(g() * vol * 0.6);
        var l = Math.min(o, c) - Math.abs(g() * vol * 0.6);
        bars.push({ t: now - (400 - k) * step, o: round(o, st.digits),
                    h: round(h, st.digits), l: round(l, st.digits),
                    c: round(c, st.digits), v: Math.floor(rnd() * 3800 + 200) });
        price = c;
      }
      candleCache[key] = bars;
    }
    var out = candleCache[key].slice(-count);
    // keep the forming bar glued to the live price
    if (out.length) {
      var lastBar = out[out.length - 1];
      var q = quote(name);
      lastBar.c = q.bid;
      lastBar.h = Math.max(lastBar.h, q.bid);
      lastBar.l = Math.min(lastBar.l, q.bid);
    }
    return out;
  }

  function livePositions() {
    return positions.map(function (p) {
      var q = quote(p.symbol);
      var cur = p.type === "buy" ? q.bid : q.ask;
      var move = p.type === "buy" ? cur - p.price_open : p.price_open - cur;
      p.price_current = cur;
      p.profit = round(move / q.trade_tick_size * q.trade_tick_value * p.volume, 2);
      return p;
    });
  }

  function account() {
    var floating = livePositions().reduce(function (a, p) { return a + p.profit; }, 0);
    var margin = positions.reduce(function (a, p) { return a + p.volume * 300; }, 0);
    var equity = balance + floating;
    return {
      login: 5000123, name: "Preview Account", server: "Preview-Server",
      currency: "USD", leverage: 500, balance: round(balance, 2),
      equity: round(equity, 2), profit: round(floating, 2),
      margin: round(margin, 2), margin_free: round(equity - margin, 2),
      margin_level: margin ? round(equity / margin * 100, 2) : 0,
      trade_allowed: true,
    };
  }

  function settle(p, price, profit, reason) {
    balance += profit;
    deals.push({ ticket: ++ticket, position: p.ticket, symbol: p.symbol,
                 type: p.type, volume: p.volume, price: price,
                 profit: round(profit, 2), commission: 0, swap: 0,
                 net: round(profit, 2), time: Math.floor(Date.now() / 1000),
                 comment: reason });
  }

  // -------------------------------------------------- indicators (strategy.py)
  function ema(v, n) {
    if (!v.length) return [];
    var k = 2 / (n + 1), out = [v[0]];
    for (var i = 1; i < v.length; i++) out.push(v[i] * k + out[i - 1] * (1 - k));
    return out;
  }
  function rsi(v, n) {
    if (v.length <= n) return v.map(function () { return null; });
    var out = new Array(n).fill(null), g = 0, l = 0, i;
    for (i = 1; i <= n; i++) {
      var d = v[i] - v[i - 1];
      g += Math.max(d, 0); l += Math.max(-d, 0);
    }
    var ag = g / n, al = l / n;
    out.push(al === 0 ? 100 : 100 - 100 / (1 + ag / al));
    for (i = n + 1; i < v.length; i++) {
      var dd = v[i] - v[i - 1];
      ag = (ag * (n - 1) + Math.max(dd, 0)) / n;
      al = (al * (n - 1) + Math.max(-dd, 0)) / n;
      out.push(al === 0 ? 100 : 100 - 100 / (1 + ag / al));
    }
    return out;
  }
  function trueRanges(c) {
    var out = [c[0].h - c[0].l];
    for (var i = 1; i < c.length; i++) {
      var pc = c[i - 1].c;
      out.push(Math.max(c[i].h - c[i].l, Math.abs(c[i].h - pc), Math.abs(c[i].l - pc)));
    }
    return out;
  }
  function atr(c, n) {
    if (c.length <= n) return c.map(function () { return null; });
    var trs = trueRanges(c), out = new Array(n - 1).fill(null), val = 0, i;
    for (i = 0; i < n; i++) val += trs[i];
    val /= n;
    out.push(val);
    for (i = n; i < trs.length; i++) { val = (val * (n - 1) + trs[i]) / n; out.push(val); }
    return out;
  }
  function macdHist(v) {
    var f = ema(v, 12), s = ema(v, 26);
    var line = f.map(function (x, i) { return x - s[i]; });
    var sig = ema(line, 9);
    return line.map(function (x, i) { return x - sig[i]; });
  }
  function adx(c, n) {
    if (c.length < n * 2 + 2) return [0, 0, 0];
    var pdm = [], mdm = [], i;
    for (i = 1; i < c.length; i++) {
      var up = c[i].h - c[i - 1].h, dn = c[i - 1].l - c[i].l;
      pdm.push(up > dn && up > 0 ? up : 0);
      mdm.push(dn > up && dn > 0 ? dn : 0);
    }
    var trs = trueRanges(c).slice(1);
    function wilder(seq) {
      var acc = 0, out = [], j;
      for (j = 0; j < n; j++) acc += seq[j];
      out.push(acc);
      for (j = n; j < seq.length; j++) { acc = acc - acc / n + seq[j]; out.push(acc); }
      return out;
    }
    var tr = wilder(trs), p = wilder(pdm), m = wilder(mdm), dxs = [];
    for (i = 0; i < tr.length; i++) {
      if (!tr[i]) { dxs.push(0); continue; }
      var pdi = 100 * p[i] / tr[i], mdi = 100 * m[i] / tr[i], den = pdi + mdi;
      dxs.push(den ? 100 * Math.abs(pdi - mdi) / den : 0);
    }
    if (dxs.length < n) return [0, 0, 0];
    var a = 0;
    for (i = 0; i < n; i++) a += dxs[i];
    a /= n;
    for (i = n; i < dxs.length; i++) a = (a * (n - 1) + dxs[i]) / n;
    var lastTr = tr[tr.length - 1] || 1e-9;
    return [a, 100 * p[p.length - 1] / lastTr, 100 * m[m.length - 1] / lastTr];
  }

  var PROFILE = {
    scalp: { minc: 72, slAtr: 1.1, tpAtr: 1.8, look: 12, slMin: 0.7, slMax: 1.6,
             minRR: 1.5, maxSpreadAtr: 0.25, minTpSpread: 5, adxMin: 20,
             regime: [0.65, 2.2], rsiL: [48, 74], rsiS: [26, 52], ext: 1.0,
             tema: [21, 55],
             w: { trend: 18, price: 12, mom: 16, rsi: 12, ma: 8, ovr: 10, adx: 14, candle: 10 } },
    trend: { minc: 70, slAtr: 1.5, tpAtr: 2.5, look: 16, slMin: 0.8, slMax: 2.5,
             minRR: 1.6, maxSpreadAtr: 0.20, minTpSpread: 4, adxMin: 18,
             regime: [0.5, 2.5], rsiL: [45, 72], rsiS: [28, 55], ext: 1.2,
             tema: [50, 200],
             w: { trend: 22, price: 13, mom: 17, rsi: 15, ma: 9, ovr: 10, adx: 8, candle: 6 } },
  };

  function analyze(entry, trendC, symbol, spread, profileName, minConf) {
    var C = PROFILE[profileName] || PROFILE.scalp;
    var res = { symbol: symbol, side: null, confidence: 0, reasons: [],
                blockers: [], atr: null, sl_points: null, tp_points: null,
                adx: null, rr: null, spread_points: null };
    if (entry.length < 60 || trendC.length < 60) {
      res.blockers.push("not_enough_history");
      return res;
    }
    var ec = entry.slice(0, -1), tc = trendC.slice(0, -1);
    var closes = ec.map(function (c) { return c.c; });
    var tcloses = tc.map(function (c) { return c.c; });
    var price = entry[entry.length - 1].c;

    var atrs = atr(ec, 14), a = atrs[atrs.length - 1];
    if (!a) { res.blockers.push("no_volatility_reading"); return res; }
    res.atr = a;

    if (spread > a * C.maxSpreadAtr) { res.blockers.push("spread_too_wide"); return res; }
    if (a * C.tpAtr < spread * C.minTpSpread) {
      res.blockers.push("target_too_small_for_spread"); return res;
    }
    var recent = atrs.slice(-50).filter(Boolean);
    var avg = recent.reduce(function (x, y) { return x + y; }, 0) / recent.length;
    if (a < avg * C.regime[0]) { res.blockers.push("market_too_quiet"); return res; }
    if (a > avg * C.regime[1]) { res.blockers.push("volatility_spike"); return res; }

    var tf = ema(tcloses, C.tema[0]), tsl = ema(tcloses, C.tema[1]);
    var lastT = tcloses[tcloses.length - 1];
    var bias;
    if (tf[tf.length - 1] > tsl[tsl.length - 1] && lastT > tsl[tsl.length - 1]) bias = "buy";
    else if (tf[tf.length - 1] < tsl[tsl.length - 1] && lastT < tsl[tsl.length - 1]) bias = "sell";
    else { res.blockers.push("higher_timeframe_undecided"); return res; }
    var long = bias === "buy";

    var e20 = ema(closes, 20), e50 = ema(closes, 50);
    var r = rsi(closes, 14), hist = macdHist(closes);
    var ax = adx(ec, 14);
    res.adx = Math.round(ax[0] * 10) / 10;
    var last = ec[ec.length - 1];
    var n = closes.length - 1;
    var band = long ? C.rsiL : C.rsiS;
    var bodyRatio = (last.h - last.l) ? Math.abs(last.c - last.o) / (last.h - last.l) : 0;
    var slope20 = (e20[n] - e20[n - 3]) / 3;

    var checks = [
      [long ? e20[n] > e50[n] : e20[n] < e50[n], C.w.trend, "entry_trend_aligned"],
      [long ? price > e20[n] : price < e20[n], C.w.price, "price_with_trend"],
      [long ? (hist[n] > 0 && hist[n] > hist[n - 1]) : (hist[n] < 0 && hist[n] < hist[n - 1]),
       C.w.mom, "momentum_building"],
      [r[n] != null && r[n] >= band[0] && r[n] <= band[1], C.w.rsi, "rsi_in_band"],
      [long ? slope20 > 0 : slope20 < 0, C.w.ma, "moving_average_turning"],
      [Math.abs(price - e20[n]) / a <= C.ext, C.w.ovr, "not_overextended"],
      [ax[0] >= C.adxMin && (long ? ax[1] > ax[2] : ax[2] > ax[1]), C.w.adx, "trend_strength"],
      [(long ? last.c > last.o : last.c < last.o) && bodyRatio >= 0.4, C.w.candle, "candle_confirms"],
    ];
    var score = 0;
    checks.forEach(function (c) {
      if (c[0]) { score += c[1]; res.reasons.push(c[2]); } else res.blockers.push(c[2]);
    });
    res.confidence = Math.round(score);
    if (score < (minConf || C.minc)) return res;

    var window_ = ec.slice(-C.look);
    var slDist = long
      ? price - Math.min.apply(null, window_.map(function (c) { return c.l; })) + a * 0.15
      : Math.max.apply(null, window_.map(function (c) { return c.h; })) - price + a * 0.15;
    slDist = Math.max(a * C.slMin, Math.min(a * C.slMax, slDist));
    var tpDist = Math.max(a * C.tpAtr, slDist * C.minRR);
    res.side = bias;
    res.sl_points = slDist;
    res.tp_points = tpDist;
    res.rr = Math.round(tpDist / slDist * 100) / 100;
    return res;
  }

  // ------------------------------------------------------------- the engine
  var bot = {
    running: false, halted_reason: "",
    config: {
      mode: "paper", profile: "scalp", symbols: ["XAUUSD"],
      entry_tf: "M5", trend_tf: "M15", min_confidence: 72,
      risk_percent: 0.5, max_open: 1, max_daily_trades: 5,
      daily_loss_percent: 2.0, max_consecutive_losses: 3, cooldown_minutes: 15,
      sl_atr: 1.1, tp_atr: 1.8, max_spread_points: 45, deviation: 15,
      partial_at_r: 1.0, partial_fraction: 0.5, break_even_at_r: 1.0,
      trail_after_r: 1.3, trail_atr: 1.0,
      sessions: [[7, 0, 20, 30]], blackouts: [[20, 45, 23, 59]],
      trade_weekend: true, interval_seconds: 10,
    },
    counters: { trades: 0, realised: 0, streak: 0 },
    scan: {}, log: [], paper: [], lastTrade: {},
  };

  function botEvent(kind, message) {
    bot.log.push({ time: Math.floor(Date.now() / 1000), kind: kind, message: message });
    if (bot.log.length > 60) bot.log.shift();
  }

  function botCycle() {
    if (!bot.running) return;
    var c = bot.config;
    // mark paper trades to market, close on SL/TP
    bot.paper = bot.paper.filter(function (p) {
      var q = quote(p.symbol);
      var cur = p.side === "buy" ? q.bid : q.ask;
      var hit = null, exit = null;
      if (p.side === "buy") {
        if (cur <= p.sl) { hit = "sl"; exit = p.sl; }
        else if (cur >= p.tp) { hit = "tp"; exit = p.tp; }
      } else {
        if (cur >= p.sl) { hit = "sl"; exit = p.sl; }
        else if (cur <= p.tp) { hit = "tp"; exit = p.tp; }
      }
      if (!hit) return true;
      var move = p.side === "buy" ? exit - p.price_open : p.price_open - exit;
      var profit = round(move / q.trade_tick_size * q.trade_tick_value * p.volume, 2);
      bot.counters.realised = round(bot.counters.realised + profit, 2);
      bot.counters.streak = profit > 0 ? 0 : bot.counters.streak + 1;
      botEvent("close", "paper " + p.side + " on " + p.symbol +
               " closed at " + hit + ": " + (profit > 0 ? "+" : "") + profit);
      return false;
    });

    (c.symbols.length ? c.symbols : WATCH).slice(0, 6).forEach(function (sym) {
      if (!state[sym]) return;
      var q = quote(sym);
      var d = analyze(candles(sym, c.entry_tf, 260), candles(sym, c.trend_tf, 260),
                      sym, q.ask - q.bid, c.profile, c.min_confidence);
      d.time = Math.floor(Date.now() / 1000);
      d.digits = q.digits;
      d.spread_points = Math.round((q.ask - q.bid) / q.point);
      bot.scan[sym] = d;

      if (!d.side) return;
      if (bot.paper.length >= c.max_open) return;
      if (bot.counters.trades >= c.max_daily_trades) return;
      if (bot.paper.some(function (p) { return p.symbol === sym; })) return;
      var since = (Date.now() / 1000) - (bot.lastTrade[sym] || 0);
      if (since < c.cooldown_minutes * 60) return;

      var entry = d.side === "buy" ? q.ask : q.bid;
      var risk = balance * c.risk_percent / 100;
      var lossPerLot = d.sl_points / q.trade_tick_size * q.trade_tick_value;
      var lot = Math.max(0.01, Math.round(risk / lossPerLot / 0.01) * 0.01);
      lot = Number(lot.toFixed(2));
      var sl = d.side === "buy" ? entry - d.sl_points : entry + d.sl_points;
      var tp = d.side === "buy" ? entry + d.tp_points : entry - d.tp_points;
      bot.paper.push({
        symbol: sym, side: d.side, volume: lot, price_open: entry,
        sl: round(sl, q.digits), tp: round(tp, q.digits), initial_sl: round(sl, q.digits),
        confidence: d.confidence, reasons: d.reasons, digits: q.digits,
        time: Math.floor(Date.now() / 1000), profit: 0, price_current: entry,
        booked: 0, be_done: false, partial_done: false,
      });
      bot.counters.trades += 1;
      bot.lastTrade[sym] = Date.now() / 1000;
      botEvent("trade", d.side + " " + sym + " " + lot.toFixed(2) + " lots at " +
               entry.toFixed(q.digits) + " — confidence " + d.confidence +
               "%, risk " + (lot * lossPerLot).toFixed(2) + ", target " + d.rr + "R");
    });
  }
  setInterval(botCycle, 4000);

  function botStatus() {
    var floating = 0;
    bot.paper.forEach(function (p) {
      var q = quote(p.symbol);
      p.price_current = p.side === "buy" ? q.bid : q.ask;
      var move = p.side === "buy" ? p.price_current - p.price_open
                                  : p.price_open - p.price_current;
      p.profit = round(move / q.trade_tick_size * q.trade_tick_value * p.volume, 2);
      floating += p.profit;
    });
    return {
      running: bot.running, halted_reason: bot.halted_reason,
      config: bot.config, profiles: ["scalp", "trend"],
      counters: bot.counters, floating: round(floating, 2),
      paper_open: bot.paper, paper_closed: [], scan: bot.scan,
      log: bot.log, last_cycle: Math.floor(Date.now() / 1000),
      cycle_error: "", session_open: true,
    };
  }

  // ------------------------------------------------------------ backtest
  var backtestState = { state: "idle", progress: 0, error: "", result: null };

  function runBacktest(cfg) {
    backtestState = { state: "running", progress: 0, error: "", result: null };
    setTimeout(function () {
      var sym = cfg.symbol || "XAUUSD";
      var c = bot.config;
      var entry = candles(sym, c.entry_tf, 400);
      var trendC = candles(sym, c.trend_tf, 400);
      var q = quote(sym);
      var spread = (cfg.spread_points || 25) * q.point;
      var bal = 10000, peak = 10000, dd = 0;
      var trades = [], curve = [{ t: entry[260].t, equity: 10000 }];
      var open = null, skipped = {};

      for (var i = 260; i < entry.length - 1; i++) {
        var bar = entry[i], nxt = entry[i + 1];
        if (open) {
          var buy = open.side === "buy";
          var hi = buy ? nxt.h : nxt.h + spread, lo = buy ? nxt.l : nxt.l + spread;
          var hitSl = buy ? lo <= open.sl : hi >= open.sl;
          var hitTp = buy ? hi >= open.tp : lo <= open.tp;
          if (hitSl || hitTp) {
            var px = hitSl ? open.sl : open.tp;
            var move = buy ? px - open.price_open : open.price_open - px;
            var profit = move / q.trade_tick_size * q.trade_tick_value * open.volume;
            bal += profit;
            peak = Math.max(peak, bal);
            dd = Math.max(dd, peak - bal);
            trades.push({ symbol: sym, side: open.side, result: hitSl ? "sl" : "tp",
                          profit: round(profit, 2),
                          r: round(profit / open.risk_amount, 2),
                          confidence: open.confidence, time: open.time,
                          close_time: nxt.t, price_open: open.price_open,
                          price_close: px, volume: open.volume });
            curve.push({ t: nxt.t, equity: round(bal, 2) });
            open = null;
          }
          continue;
        }
        var ti = trendC.findIndex(function (x) { return x.t > bar.t; });
        if (ti < 60) ti = Math.min(trendC.length, Math.max(60, Math.floor(i / 3)));
        var d = analyze(entry.slice(Math.max(0, i - 259), i + 2),
                        trendC.slice(Math.max(0, ti - 260), ti),
                        sym, spread, c.profile, c.min_confidence);
        if (!d.side) {
          if (d.blockers.length) skipped[d.blockers[0]] = (skipped[d.blockers[0]] || 0) + 1;
          continue;
        }
        var fill = d.side === "buy" ? nxt.o + spread : nxt.o;
        var lossPerLot = d.sl_points / q.trade_tick_size * q.trade_tick_value;
        var lot = Math.max(0.01, Math.round(bal * 0.005 / lossPerLot / 0.01) * 0.01);
        open = {
          side: d.side, price_open: fill, volume: Number(lot.toFixed(2)),
          sl: d.side === "buy" ? fill - d.sl_points : fill + d.sl_points,
          tp: d.side === "buy" ? fill + d.tp_points : fill - d.tp_points,
          confidence: d.confidence, time: nxt.t,
          risk_amount: lot * lossPerLot,
        };
      }

      var nets = trades.map(function (t) { return t.profit; });
      var wins = nets.filter(function (x) { return x > 0; });
      var losses = nets.filter(function (x) { return x <= 0; });
      var gw = wins.reduce(function (a, b) { return a + b; }, 0);
      var gl = -losses.reduce(function (a, b) { return a + b; }, 0);
      var streak = 0, worst = 0;
      nets.forEach(function (x) { streak = x <= 0 ? streak + 1 : 0; worst = Math.max(worst, streak); });
      backtestState = {
        state: "done", progress: 1, error: "",
        result: {
          symbol: sym, entry_tf: c.entry_tf, trend_tf: c.trend_tf,
          profile: c.profile, bars: entry.length,
          spread_points: cfg.spread_points || 25,
          from: entry[260].t, to: entry[entry.length - 1].t,
          start_balance: 10000, end_balance: round(bal, 2),
          stats: {
            count: trades.length,
            win_rate: nets.length ? round(wins.length / nets.length * 100, 1) : 0,
            profit_factor: gl ? round(gw / gl, 2) : 0,
            net: round(bal - 10000, 2),
            net_percent: round((bal / 10000 - 1) * 100, 2),
            max_drawdown: round(dd, 2),
            max_drawdown_percent: round(dd / 100, 2),
            expectancy_r: nets.length
              ? round(trades.reduce(function (a, t) { return a + t.r; }, 0) / trades.length, 3) : 0,
            best: nets.length ? round(Math.max.apply(null, nets), 2) : 0,
            worst: nets.length ? round(Math.min.apply(null, nets), 2) : 0,
            longest_losing_streak: worst,
          },
          trades: trades.slice(-200), curve: curve,
          skipped: Object.keys(skipped).map(function (k) { return [k, skipped[k]]; })
            .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8),
        },
      };
    }, 900);
  }

  // ---------------------------------------------------------- fetch shim
  function ok(data) {
    return Promise.resolve({
      ok: true, status: 200,
      json: function () { return Promise.resolve({ ok: true, data: data }); },
    });
  }
  function fail(message) {
    return Promise.resolve({
      ok: false, status: 400,
      json: function () { return Promise.resolve({ ok: false, error: message }); },
    });
  }

  var realFetch = window.fetch ? window.fetch.bind(window) : null;

  window.fetch = function (url, opts) {
    var path = String(url).split("?")[0];
    if (path.indexOf("/api/") !== 0) {
      return realFetch ? realFetch(url, opts) : fail("offline");
    }
    var query = {};
    String(url).split("?").slice(1).join("?").split("&").forEach(function (pair) {
      if (!pair) return;
      var kv = pair.split("=");
      query[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
    });
    var body = {};
    if (opts && opts.body) { try { body = JSON.parse(opts.body); } catch (e) { body = {}; } }
    var p = Object.assign({}, query, body);

    switch (path) {
      case "/api/needs_login":
        return ok({ password_required: false, authorised: true });
      case "/api/status":
        return ok({ connected: true, demo: true,
                    terminal: { name: "Preview", company: "browser preview",
                                build: 0, trade_allowed: true, connected: true },
                    account: account() });
      case "/api/account":
        return ok(account());
      case "/api/symbols":
        var all = String(p.all) === "1";
        var names = all ? Object.keys(SPECS) : WATCH;
        if (p.q) {
          var needle = String(p.q).toLowerCase();
          names = names.filter(function (n) {
            return n.toLowerCase().indexOf(needle) >= 0 ||
                   SPECS[n][5].toLowerCase().indexOf(needle) >= 0;
          });
        }
        return ok({ symbols: names.map(quote) });
      case "/api/symbol":
        return state[p.symbol] ? ok(quote(p.symbol)) : fail("Unknown symbol: " + p.symbol);
      case "/api/candles":
        if (!state[p.symbol]) return fail("Unknown symbol: " + p.symbol);
        return ok({ candles: candles(p.symbol, p.tf || "M15", parseInt(p.count, 10) || 180) });
      case "/api/snapshot":
        return ok({ account: account(), positions: livePositions(), orders: orders,
                    symbols: WATCH.map(quote), demo: true,
                    bot: { running: bot.running, mode: bot.config.mode,
                           halted_reason: bot.halted_reason,
                           trades_today: bot.counters.trades } });
      case "/api/history":
        var days = parseInt(p.days, 10) || 30;
        var cutoff = Date.now() / 1000 - days * 86400;
        var list = deals.filter(function (d) { return d.time >= cutoff; })
                        .sort(function (a, b) { return b.time - a.time; });
        var w = list.filter(function (d) { return d.net > 0; });
        var l = list.filter(function (d) { return d.net < 0; });
        var gwin = w.reduce(function (a, d) { return a + d.net; }, 0);
        var gloss = -l.reduce(function (a, d) { return a + d.net; }, 0);
        return ok({ deals: list, totals: {
          count: list.length,
          net: round(list.reduce(function (a, d) { return a + d.net; }, 0), 2),
          wins: w.length, losses: l.length,
          win_rate: list.length ? w.length / list.length * 100 : 0,
          best: list.length ? Math.max.apply(null, list.map(function (d) { return d.net; })) : 0,
          worst: list.length ? Math.min.apply(null, list.map(function (d) { return d.net; })) : 0,
          gross_win: gwin, gross_loss: gloss,
          profit_factor: gloss ? gwin / gloss : 0,
          volume: round(list.reduce(function (a, d) { return a + d.volume; }, 0), 2),
        } });
      case "/api/calc_lot":
        if (!state[p.symbol]) return fail("Unknown symbol: " + p.symbol);
        var qq = quote(p.symbol);
        var slPts = parseFloat(p.sl_points);
        if (!slPts || slPts <= 0) return fail("Stop loss distance must be greater than zero.");
        var perLot = slPts * qq.point / qq.trade_tick_size * qq.trade_tick_value;
        var raw = parseFloat(p.risk) / perLot;
        var lotv = Math.max(0.01, Math.round(raw / 0.01) * 0.01);
        return ok({ symbol: p.symbol, lot: Number(lotv.toFixed(2)), raw_lot: raw,
                    loss_per_lot: perLot, estimated_loss: lotv * perLot,
                    volume_min: 0.01, volume_step: 0.01 });
      case "/api/select":
        var enable = p.enable === true || p.enable === "1" || p.enable === "true";
        var at = WATCH.indexOf(p.symbol);
        if (enable && at < 0) WATCH.push(p.symbol);
        if (!enable && at >= 0) WATCH.splice(at, 1);
        return ok({ symbol: p.symbol, visible: enable });
      case "/api/order":
        if (!state[p.symbol]) return fail("Unknown symbol: " + p.symbol);
        var oq = quote(p.symbol);
        var side = String(p.side).toLowerCase();
        var openPrice = side === "buy" ? oq.ask : oq.bid;
        positions.push({ ticket: ++ticket, symbol: p.symbol, type: side,
                         volume: Number(p.volume), price_open: openPrice,
                         price_current: openPrice, sl: Number(p.sl) || 0,
                         tp: Number(p.tp) || 0, profit: 0, swap: 0,
                         time: Math.floor(Date.now() / 1000),
                         comment: "preview", digits: oq.digits });
        return ok({ retcode: 10009, deal: ticket, order: ticket,
                    price: openPrice, volume: Number(p.volume), comment: "preview filled" });
      case "/api/pending":
        var pq = quote(p.symbol);
        orders.push({ ticket: ++ticket, symbol: p.symbol,
                      type: String(p.type).toLowerCase(), volume: Number(p.volume),
                      price_open: Number(p.price), sl: Number(p.sl) || 0,
                      tp: Number(p.tp) || 0, time: Math.floor(Date.now() / 1000),
                      digits: pq.digits });
        return ok({ retcode: 10009, order: ticket, price: Number(p.price),
                    volume: Number(p.volume), comment: "preview placed" });
      case "/api/modify":
        var mp = positions.find(function (x) { return x.ticket === Number(p.ticket); });
        if (!mp) return fail("Position not found");
        mp.sl = Number(p.sl) || 0;
        mp.tp = Number(p.tp) || 0;
        return ok({ retcode: 10009, order: mp.ticket, comment: "preview modified" });
      case "/api/close":
        livePositions();
        var idx = positions.findIndex(function (x) { return x.ticket === Number(p.ticket); });
        if (idx < 0) return fail("Position not found");
        var cp = positions[idx];
        var part = p.volume ? Math.min(Number(p.volume), cp.volume) : cp.volume;
        var share = cp.profit * (part / cp.volume);
        settle(Object.assign({}, cp, { volume: part }), cp.price_current, share, "close");
        if (part >= cp.volume - 1e-9) positions.splice(idx, 1);
        else cp.volume = round(cp.volume - part, 2);
        return ok({ retcode: 10009, price: cp.price_current, volume: part,
                    comment: "preview closed" });
      case "/api/close_all":
        livePositions();
        positions.slice().forEach(function (x) {
          settle(x, x.price_current, x.profit, "close");
        });
        positions = [];
        return ok({ closed: [] });
      case "/api/cancel":
        var oi = orders.findIndex(function (x) { return x.ticket === Number(p.ticket); });
        if (oi < 0) return fail("Order not found");
        orders.splice(oi, 1);
        return ok({ retcode: 10009, comment: "preview cancelled" });
      case "/api/bot":
        return ok(botStatus());
      case "/api/bot/start":
        bot.running = true;
        botEvent("start", "engine started in paper mode (" + bot.config.profile +
                 " profile, " + bot.config.symbols.join(", ") + ")");
        botCycle();
        return ok(botStatus());
      case "/api/bot/stop":
        if (bot.running) botEvent("stop", "stopped by user");
        bot.running = false;
        return ok(botStatus());
      case "/api/bot/config":
        if (p.profile && p.profile !== bot.config.profile) {
          if (p.profile !== "scalp" && p.profile !== "trend") {
            return fail("profile must be scalp or trend");
          }
          bot.config.profile = p.profile;
          var def = p.profile === "scalp"
            ? { entry_tf: "M5", trend_tf: "M15", min_confidence: 72, sl_atr: 1.1, tp_atr: 1.8 }
            : { entry_tf: "M15", trend_tf: "H1", min_confidence: 70, sl_atr: 1.5, tp_atr: 2.5 };
          Object.assign(bot.config, def);
          botEvent("profile", "switched to the " + p.profile + " profile");
        }
        Object.keys(p).forEach(function (k) {
          if (k === "profile" || !(k in bot.config)) return;
          if (k === "mode") {
            if (p[k] !== "paper") {
              botEvent("mode", "live mode is not available in the preview");
              return;
            }
          }
          bot.config[k] = p[k];
        });
        return ok(botStatus());
      case "/api/bot/resume":
        bot.halted_reason = "";
        bot.counters.streak = 0;
        return ok(botStatus());
      case "/api/backtest":
        return ok(backtestState);
      case "/api/backtest/start":
        if (backtestState.state === "running") return fail("A backtest is already running");
        runBacktest(p);
        return ok(backtestState);
      case "/api/backtest/cancel":
        backtestState = { state: "idle", progress: 0, error: "", result: null };
        return ok(backtestState);
      default:
        return fail("Unknown endpoint: " + path);
    }
  };

  // seed a little history so the panel does not open empty
  (function seed() {
    ["XAUUSD", "EURUSD"].forEach(function (sym, i) {
      var q = quote(sym);
      var side = i ? "sell" : "buy";
      positions.push({
        ticket: ++ticket, symbol: sym, type: side, volume: i ? 0.10 : 0.05,
        price_open: side === "buy" ? q.ask : q.bid,
        price_current: side === "buy" ? q.bid : q.ask,
        sl: 0, tp: 0, profit: 0, swap: 0,
        time: Math.floor(Date.now() / 1000) - 3600 * (i + 1),
        comment: "preview", digits: q.digits,
      });
    });
    var now = Math.floor(Date.now() / 1000);
    [[-42.5, "XAUUSD", 6], [88.2, "XAUUSD", 20], [-31.0, "EURUSD", 30],
     [64.8, "XAUUSD", 45], [22.4, "GBPUSD", 60]].forEach(function (d, i) {
      deals.push({ ticket: ++ticket, position: 0, symbol: d[1],
                   type: i % 2 ? "sell" : "buy", volume: 0.05, price: quote(d[1]).bid,
                   profit: d[0], commission: 0, swap: 0, net: d[0],
                   time: now - d[2] * 3600, comment: "close" });
    });
  })();
})();
