/* MT5 Panel — phone-style front end.
   Talks only to the local python server (server.py) on 127.0.0.1. */

(function () {
  "use strict";

  // ------------------------------------------------------------------ state
  var KEY = window.PANEL_KEY || new URLSearchParams(location.search).get("k") || "";
  if (/^_+PANEL_KEY_+$/.test(KEY)) KEY = "";   // template not substituted

  var S = {
    lang: localStorage.getItem("mt5panel.lang") || "ar",
    theme: localStorage.getItem("mt5panel.theme") || "dark",
    wide: localStorage.getItem("mt5panel.wide") === "1",
    refresh: parseInt(localStorage.getItem("mt5panel.refresh") || "1500", 10),
    view: "quotes",
    snap: null,
    status: null,
    chartSymbol: localStorage.getItem("mt5panel.chartSymbol") || "",
    tf: localStorage.getItem("mt5panel.tf") || "M15",
    candles: [],
    historyDays: 30,
    history: null,
    lastError: "",
    busy: false,
  };

  var $ = function (id) { return document.getElementById(id); };
  var TFS = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"];

  function t(key, vars) {
    var dict = window.I18N[S.lang] || window.I18N.en;
    var s = dict[key] != null ? dict[key] : (window.I18N.en[key] || key);
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        s = s.split("{" + k + "}").join(vars[k]);
      });
    }
    return s;
  }

  // ------------------------------------------------------------------- api
  function api(path, params, method) {
    var opts = { method: method || "GET", headers: { "X-Panel-Key": KEY } };
    var url = path;
    if (method === "POST") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(params || {});
    } else if (params) {
      var q = new URLSearchParams(params).toString();
      if (q) url += "?" + q;
    }
    return fetch(url, opts).then(function (res) {
      return res.json().catch(function () {
        throw new Error("HTTP " + res.status);
      }).then(function (body) {
        if (!res.ok || body.ok === false) {
          throw new Error(body.error || ("HTTP " + res.status));
        }
        return body.data;
      });
    });
  }

  // -------------------------------------------------------------- helpers
  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return "—";
    return Number(n).toLocaleString("en-US", {
      minimumFractionDigits: d == null ? 2 : d,
      maximumFractionDigits: d == null ? 2 : d,
    });
  }
  function money(n, d) { return (n > 0 ? "+" : "") + fmt(n, d == null ? 2 : d); }
  function cls(n) { return n > 0 ? "up" : (n < 0 ? "down" : ""); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function timeStr(unix) {
    var d = new Date(unix * 1000);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) +
      " " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  }
  function ccy() {
    return (S.snap && S.snap.account && S.snap.account.currency) || "";
  }

  var toastTimer = null;
  function toast(msg, kind) {
    var el = $("toast");
    el.textContent = msg;
    el.className = "show " + (kind || "");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.className = ""; }, 3200);
  }

  function symbolOf(name) {
    if (!S.snap) return null;
    for (var i = 0; i < S.snap.symbols.length; i++) {
      if (S.snap.symbols[i].symbol === name) return S.snap.symbols[i];
    }
    return null;
  }

  // ------------------------------------------------------------------ sheet
  function openSheet(title, node) {
    $("sheet-title").textContent = title;
    var body = $("sheet-body");
    body.innerHTML = "";
    body.appendChild(node);
    $("scrim").classList.add("open");
    $("sheet").classList.add("open");
  }
  function closeSheet() {
    $("scrim").classList.remove("open");
    $("sheet").classList.remove("open");
    sheetTick = null;
  }
  var sheetTick = null;   // optional per-sheet live update callback

  function el(html) {
    var d = document.createElement("div");
    d.innerHTML = html.trim();
    return d.childNodes.length === 1 ? d.firstChild : d;
  }

  function confirmAction(message, onYes) {
    var node = el(
      '<div><p style="font-size:15px;line-height:1.7;margin-bottom:16px">' +
      esc(message) + '</p>' +
      '<div class="two-col">' +
      '<button class="btn-line" data-no>' + esc(t("cancel")) + '</button>' +
      '<button class="btn-line danger" data-yes>' + esc(t("confirm_yes")) + '</button>' +
      '</div></div>');
    node.querySelector("[data-no]").onclick = closeSheet;
    node.querySelector("[data-yes]").onclick = function () { closeSheet(); onYes(); };
    openSheet(t("confirm_title"), node);
  }

  // ------------------------------------------------------------ rendering
  function renderTopbar() {
    var st = S.status;
    var dot = $("conn-dot");
    var connected = st && st.connected;
    dot.className = "dot " + (connected ? "on" : "off");
    $("hdr-title").textContent = t("app_title");
    var sub;
    if (!connected) {
      sub = S.lastError || t("disconnected");
    } else if (st.demo) {
      sub = t("demo_mode");
    } else {
      var a = st.account || {};
      sub = "#" + a.login + " · " + a.server;
    }
    $("hdr-sub").textContent = sub;
    $("btn-lang").textContent = t("_other");
  }

  function renderQuotes() {
    var actions = $("quotes-actions");
    if (!actions.dataset.built) {
      actions.dataset.built = "1";
      var b = el('<button class="chip">+ ' + esc(t("add_symbol")) + "</button>");
      b.onclick = openSymbolSearch;
      actions.appendChild(b);
    } else {
      actions.firstChild.textContent = "+ " + t("add_symbol");
    }

    var list = $("quotes-list");
    var syms = (S.snap && S.snap.symbols) || [];
    if (!syms.length) {
      list.innerHTML = '<div class="empty">' + esc(t("no_symbols")).replace(/\n/g, "<br>") + "</div>";
      return;
    }
    list.innerHTML = "";
    syms.forEach(function (s) {
      var row = el(
        '<button class="row">' +
        '<div class="grow">' +
        '<div class="name">' + esc(s.symbol) + "</div>" +
        '<div class="meta numeric">' + esc(t("spread")) + ": " + s.spread + "</div>" +
        "</div>" +
        '<div class="price-pair">' +
        '<div class="price bid numeric"><small>' + esc(t("bid")) + "</small>" +
        fmt(s.bid, s.digits) + "</div>" +
        '<div class="price ask numeric"><small>' + esc(t("ask")) + "</small>" +
        fmt(s.ask, s.digits) + "</div>" +
        "</div></button>");
      row.onclick = function () { openSymbolSheet(s.symbol); };
      list.appendChild(row);
    });
  }

  function renderTrade() {
    var a = S.snap && S.snap.account;
    var card = $("account-card");
    if (!a) {
      card.innerHTML = '<div class="empty">' + esc(t("connecting")) + "</div>";
    } else {
      card.innerHTML =
        '<div class="acct-label">' + esc(t("equity")) + "</div>" +
        '<div class="acct-equity numeric">' + fmt(a.equity) + " " + esc(a.currency) + "</div>" +
        '<div class="acct-grid">' +
        kv(t("balance"), fmt(a.balance)) +
        kv(t("floating_pl"), money(a.profit), cls(a.profit)) +
        kv(t("margin"), fmt(a.margin)) +
        kv(t("free_margin"), fmt(a.margin_free)) +
        kv(t("margin_level"), a.margin_level ? fmt(a.margin_level) + "%" : "—") +
        kv(t("leverage"), "1:" + a.leverage) +
        "</div>";
    }

    $("t-positions").textContent = t("positions");
    $("t-orders").textContent = t("pending_orders");
    $("btn-close-all").textContent = t("close_all");

    var plist = $("positions-list");
    var pos = (S.snap && S.snap.positions) || [];
    if (!pos.length) {
      plist.innerHTML = '<div class="empty">' + esc(t("no_positions")) + "</div>";
    } else {
      plist.innerHTML = "";
      pos.forEach(function (p) {
        var row = el(
          '<button class="row">' +
          '<div class="grow">' +
          '<div class="name">' + esc(p.symbol) +
          ' <span class="pill ' + p.type + '">' + esc(t(p.type)) + " " +
          fmt(p.volume, 2) + "</span></div>" +
          '<div class="meta numeric">' + fmt(p.price_open, p.digits) +
          " → " + fmt(p.price_current, p.digits) +
          (p.sl ? " · SL " + fmt(p.sl, p.digits) : "") +
          (p.tp ? " · TP " + fmt(p.tp, p.digits) : "") + "</div>" +
          "</div>" +
          '<div class="price numeric ' + cls(p.profit) + '">' + money(p.profit) + "</div>" +
          "</button>");
        row.onclick = function () { openPositionSheet(p.ticket); };
        plist.appendChild(row);
      });
    }

    var olist = $("orders-list");
    var ords = (S.snap && S.snap.orders) || [];
    if (!ords.length) {
      olist.innerHTML = '<div class="empty">' + esc(t("no_orders")) + "</div>";
    } else {
      olist.innerHTML = "";
      ords.forEach(function (o) {
        var side = o.type.indexOf("buy") === 0 ? "buy" : "sell";
        var row = el(
          '<button class="row">' +
          '<div class="grow"><div class="name">' + esc(o.symbol) +
          ' <span class="pill ' + side + '">' + esc(o.type.replace("_", " ")) +
          " " + fmt(o.volume, 2) + "</span></div>" +
          '<div class="meta numeric">@ ' + fmt(o.price_open, o.digits) +
          " · " + timeStr(o.time) + "</div></div>" +
          '<div class="pill">✕</div></button>');
        row.onclick = function () { openCancelSheet(o); };
        olist.appendChild(row);
      });
    }
  }

  function kv(k, v, extra) {
    return '<div><span class="k">' + esc(k) + '</span>' +
      '<span class="v numeric ' + (extra || "") + '">' + v + "</span></div>";
  }

  function renderHistory() {
    var chips = $("history-chips");
    chips.innerHTML = "";
    [[1, "today"], [7, "week"], [30, "month"], [90, "months3"]].forEach(function (pair) {
      var c = el('<button class="chip' + (S.historyDays === pair[0] ? " active" : "") +
        '">' + esc(t(pair[1])) + "</button>");
      c.onclick = function () { S.historyDays = pair[0]; loadHistory(); };
      chips.appendChild(c);
    });

    var tot = $("history-totals");
    var list = $("history-list");
    if (!S.history) {
      tot.innerHTML = '<div class="empty">' + esc(t("connecting")) + "</div>";
      list.innerHTML = "";
      return;
    }
    var T = S.history.totals;
    tot.innerHTML =
      '<div style="padding:16px">' +
      '<div class="acct-label">' + esc(t("net_profit")) + "</div>" +
      '<div class="acct-equity numeric ' + cls(T.net) + '">' + money(T.net) +
      " " + esc(ccy()) + "</div>" +
      '<div class="acct-grid">' +
      kv(t("trades"), T.count) +
      kv(t("win_rate"), fmt(T.win_rate, 1) + "%") +
      kv(t("best_trade"), money(T.best), cls(T.best)) +
      kv(t("worst_trade"), money(T.worst), cls(T.worst)) +
      kv(t("profit_factor"), T.profit_factor ? fmt(T.profit_factor, 2) : "—") +
      kv(t("volume"), fmt(T.volume, 2)) +
      "</div></div>";

    var deals = S.history.deals;
    if (!deals.length) {
      list.innerHTML = '<div class="empty">' + esc(t("no_history")) + "</div>";
      return;
    }
    list.innerHTML = "";
    deals.forEach(function (d) {
      list.appendChild(el(
        '<div class="row" style="cursor:default">' +
        '<div class="grow"><div class="name">' + esc(d.symbol) +
        ' <span class="pill ' + d.type + '">' + fmt(d.volume, 2) + "</span></div>" +
        '<div class="meta numeric">' + timeStr(d.time) + " · " + fmt(d.price, 5) + "</div></div>" +
        '<div class="price numeric ' + cls(d.net) + '">' + money(d.net) + "</div></div>"));
    });
  }

  function renderSettings() {
    $("t-appearance").textContent = t("appearance");
    $("t-connection").textContent = t("connection");
    $("t-about").textContent = t("about");
    $("about-text").textContent = t("about_text");

    var ap = $("settings-appearance");
    ap.innerHTML = "";
    ap.appendChild(segRow(t("language"), "", [["ar", "العربية"], ["en", "English"]],
      S.lang, function (v) { setLang(v); }));
    ap.appendChild(segRow(t("theme"), "", [["dark", t("dark")], ["light", t("light")]],
      S.theme, function (v) {
        S.theme = v; localStorage.setItem("mt5panel.theme", v);
        document.documentElement.setAttribute("data-theme", v); renderSettings();
      }));
    ap.appendChild(segRow(t("width"), "", [["0", t("phone")], ["1", t("wide")]],
      S.wide ? "1" : "0", function (v) {
        S.wide = v === "1"; localStorage.setItem("mt5panel.wide", v);
        document.body.classList.toggle("wide", S.wide);
        renderSettings(); drawChart();
      }));
    ap.appendChild(segRow(t("refresh_rate"), "",
      [["1000", "1s"], ["1500", "1.5s"], ["3000", "3s"], ["6000", "6s"]],
      String(S.refresh), function (v) {
        S.refresh = parseInt(v, 10);
        localStorage.setItem("mt5panel.refresh", v);
        restartPolling(); renderSettings();
      }));

    var cn = $("settings-connection");
    var st = S.status || {};
    var a = st.account || {};
    var term = st.terminal || {};
    cn.innerHTML =
      infoRow(t("connected"), st.connected ? "✓ " + t("connected") : "✕ " + t("disconnected")) +
      (st.demo ? infoRow("—", t("demo_mode")) : "") +
      infoRow(t("account"), a.login ? "#" + a.login + " · " + esc(a.name || "") : "—") +
      infoRow(t("server"), esc(a.server || "—")) +
      infoRow(t("currency"), esc(a.currency || "—")) +
      infoRow(t("terminal"), esc((term.company || "—") + (term.build ? " · " + term.build : "")));
  }

  function infoRow(k, v) {
    return '<div class="switch-row"><div><div class="k">' + esc(k) +
      '</div></div><div class="numeric" style="font-size:13px;color:var(--ink-2)">' +
      v + "</div></div>";
  }

  function segRow(title, desc, options, current, onPick) {
    var wrap = el('<div class="switch-row"><div><div class="k">' + esc(title) +
      '</div>' + (desc ? '<div class="d">' + esc(desc) + "</div>" : "") +
      '</div><div class="seg"></div></div>');
    var seg = wrap.querySelector(".seg");
    options.forEach(function (o) {
      var b = el('<button' + (String(current) === String(o[0]) ? ' class="active"' : "") +
        ">" + esc(o[1]) + "</button>");
      b.onclick = function () { onPick(o[0]); };
      seg.appendChild(b);
    });
    return wrap;
  }

  function renderStaticText() {
    document.querySelectorAll("[data-i18n]").forEach(function (n) {
      n.textContent = t(n.getAttribute("data-i18n"));
    });
    document.title = t("app_title");
  }

  function renderCurrentView() {
    renderTopbar();
    if (S.view === "quotes") renderQuotes();
    else if (S.view === "trade") renderTrade();
    else if (S.view === "history") renderHistory();
    else if (S.view === "settings") renderSettings();
    else if (S.view === "chart") renderChartHead();
    if (sheetTick) sheetTick();
  }

  // ------------------------------------------------------------- symbol sheet
  function openSymbolSheet(name) {
    var s = symbolOf(name);
    if (!s) return;
    newOrderSheet(name);
  }

  function openSymbolSearch() {
    var node = el(
      '<div>' +
      '<div class="field"><input type="text" id="sym-q" placeholder="' +
      esc(t("search_symbol")) + '"></div>' +
      '<div id="sym-results"></div></div>');
    var input = node.querySelector("#sym-q");
    var results = node.querySelector("#sym-results");
    var timer = null;

    function search() {
      var q = input.value.trim();
      api("/api/symbols", { all: "1", q: q }).then(function (d) {
        results.innerHTML = "";
        if (!d.symbols.length) {
          results.innerHTML = '<div class="empty">—</div>';
          return;
        }
        d.symbols.slice(0, 60).forEach(function (s) {
          var row = el('<button class="row"><div class="grow">' +
            '<div class="name">' + esc(s.symbol) + "</div>" +
            '<div class="meta">' + esc(s.description || "") + "</div></div>" +
            '<div class="pill">' + (s.visible ? "✓" : "+") + "</div></button>");
          row.onclick = function () {
            api("/api/select", { symbol: s.symbol, enable: !s.visible }, "POST")
              .then(function () {
                toast(s.visible ? t("removed") : t("added"), "ok");
                refresh(); search();
              })
              .catch(function (e) { toast(e.message, "err"); });
          };
          results.appendChild(row);
        });
      }).catch(function (e) { toast(e.message, "err"); });
    }

    input.oninput = function () { clearTimeout(timer); timer = setTimeout(search, 250); };
    openSheet(t("add_symbol"), node);
    search();
    setTimeout(function () { input.focus(); }, 60);
  }

  // -------------------------------------------------------- new order sheet
  function newOrderSheet(symbolName) {
    var syms = (S.snap && S.snap.symbols) || [];
    if (!syms.length) { toast(t("no_symbols"), "err"); return; }
    var current = symbolOf(symbolName) || syms[0];
    var slMode = "points", tpMode = "points";

    var node = el(
      '<div>' +
      '<div class="field"><label>' + esc(t("symbol")) + '</label>' +
      '<select id="o-sym"></select></div>' +

      '<div class="field"><label>' + esc(t("lot")) + '</label>' +
      '<div class="stepper">' +
      '<button type="button" id="o-minus">−</button>' +
      '<input type="number" id="o-vol" step="0.01" min="0.01" value="0.01">' +
      '<button type="button" id="o-plus">+</button>' +
      '</div></div>' +

      '<div class="two-col">' +
      '<div class="field"><label>' + esc(t("sl")) + ' <button type="button" class="pill" id="o-slmode"></button></label>' +
      '<input type="number" id="o-sl" placeholder="—"></div>' +
      '<div class="field"><label>' + esc(t("tp")) + ' <button type="button" class="pill" id="o-tpmode"></button></label>' +
      '<input type="number" id="o-tp" placeholder="—"></div>' +
      "</div>" +
      '<p class="note">' + esc(t("sl_tp_hint")) + "</p>" +

      '<div class="field" style="margin-top:14px">' +
      '<button type="button" class="btn-line" id="o-riskbtn">⚖︎ ' + esc(t("risk_calc")) + "</button>" +
      '<div id="o-riskbox" style="display:none;margin-top:10px">' +
      '<div class="two-col">' +
      '<div class="field"><label>' + esc(t("risk_percent")) + '</label>' +
      '<input type="number" id="o-riskpct" value="1" step="0.1" min="0.1"></div>' +
      '<div class="field"><label>' + esc(t("risk_amount")) + '</label>' +
      '<input type="number" id="o-riskamt" placeholder="—"></div>' +
      "</div>" +
      '<button type="button" class="btn-line" id="o-calc">' + esc(t("calc")) + "</button>" +
      '<p class="note" id="o-calcout" style="margin-top:8px"></p>' +
      "</div></div>" +

      '<div class="trade-buttons">' +
      '<button class="big-btn sell" id="o-sell">' + esc(t("sell")) +
      '<small class="numeric" id="o-bid">—</small></button>' +
      '<button class="big-btn buy" id="o-buy">' + esc(t("buy")) +
      '<small class="numeric" id="o-ask">—</small></button>' +
      "</div>" +
      '<p class="warn" id="o-warn"></p>' +
      "</div>");

    var selSym = node.querySelector("#o-sym");
    syms.forEach(function (s) {
      var opt = document.createElement("option");
      opt.value = s.symbol;
      opt.textContent = s.symbol;
      if (s.symbol === current.symbol) opt.selected = true;
      selSym.appendChild(opt);
    });

    var volInput = node.querySelector("#o-vol");
    volInput.value = current.volume_min || 0.01;
    volInput.step = current.volume_step || 0.01;
    volInput.min = current.volume_min || 0.01;

    function step(dir) {
      var s = symbolOf(selSym.value) || current;
      var stp = s.volume_step || 0.01;
      var v = (parseFloat(volInput.value) || 0) + dir * stp;
      var decimals = (String(stp).split(".")[1] || "").length;
      v = Math.max(s.volume_min, Math.min(s.volume_max, v));
      volInput.value = v.toFixed(decimals);
    }
    node.querySelector("#o-minus").onclick = function () { step(-1); };
    node.querySelector("#o-plus").onclick = function () { step(1); };

    var slModeBtn = node.querySelector("#o-slmode");
    var tpModeBtn = node.querySelector("#o-tpmode");
    function paintModes() {
      slModeBtn.textContent = slMode === "points" ? t("points") : t("price_word");
      tpModeBtn.textContent = tpMode === "points" ? t("points") : t("price_word");
    }
    slModeBtn.onclick = function () {
      slMode = slMode === "points" ? "price" : "points"; paintModes();
    };
    tpModeBtn.onclick = function () {
      tpMode = tpMode === "points" ? "price" : "points"; paintModes();
    };
    paintModes();

    node.querySelector("#o-riskbtn").onclick = function () {
      var box = node.querySelector("#o-riskbox");
      box.style.display = box.style.display === "none" ? "block" : "none";
    };
    node.querySelector("#o-calc").onclick = function () {
      var s = symbolOf(selSym.value);
      var acct = S.snap.account;
      var amt = parseFloat(node.querySelector("#o-riskamt").value);
      if (!amt) {
        var pct = parseFloat(node.querySelector("#o-riskpct").value) || 0;
        amt = acct.balance * pct / 100;
      }
      var slRaw = parseFloat(node.querySelector("#o-sl").value);
      if (!slRaw) { toast(t("sl") + " ?", "err"); return; }
      var slPoints = slMode === "points"
        ? slRaw
        : Math.abs(slRaw - s.bid) / s.point;
      api("/api/calc_lot", { symbol: s.symbol, risk: amt, sl_points: slPoints })
        .then(function (r) {
          volInput.value = r.lot;
          node.querySelector("#o-calcout").textContent =
            t("calc_result", { lot: r.lot, loss: fmt(r.estimated_loss) + " " + ccy() });
        })
        .catch(function (e) { toast(e.message, "err"); });
    };

    function priceFor(field, mode, side) {
      // returns an absolute price, or null when the field is empty
      var s = symbolOf(selSym.value);
      var raw = parseFloat(node.querySelector(field).value);
      if (!raw) return null;
      if (mode === "price") return raw;
      var entry = side === "buy" ? s.ask : s.bid;
      var dist = raw * s.point;
      var isSL = field === "#o-sl";
      if (side === "buy") return isSL ? entry - dist : entry + dist;
      return isSL ? entry + dist : entry - dist;
    }

    function send(side) {
      var s = symbolOf(selSym.value);
      var vol = parseFloat(volInput.value);
      if (!vol || vol <= 0) { toast(t("volume"), "err"); return; }
      var payload = {
        symbol: s.symbol, side: side, volume: vol,
        sl: priceFor("#o-sl", slMode, side),
        tp: priceFor("#o-tp", tpMode, side),
      };
      confirmAction(
        t("confirm_order", { side: t(side), vol: vol, sym: s.symbol }),
        function () {
          S.busy = true;
          api("/api/order", payload, "POST").then(function (r) {
            toast(t("order_done") + " @ " + fmt(r.price, s.digits), "ok");
            refresh(); switchView("trade");
          }).catch(function (e) {
            toast(t("order_failed") + ": " + e.message, "err");
          }).then(function () { S.busy = false; });
        });
    }
    node.querySelector("#o-sell").onclick = function () { send("sell"); };
    node.querySelector("#o-buy").onclick = function () { send("buy"); };

    selSym.onchange = function () {
      var s = symbolOf(selSym.value);
      volInput.value = s.volume_min;
      volInput.step = s.volume_step;
      tick();
    };

    function tick() {
      var s = symbolOf(selSym.value);
      if (!s) return;
      node.querySelector("#o-bid").textContent = fmt(s.bid, s.digits);
      node.querySelector("#o-ask").textContent = fmt(s.ask, s.digits);
    }

    openSheet(t("new_order"), node);
    sheetTick = tick;
    tick();
  }

  // ------------------------------------------------------ position sheet
  function openPositionSheet(ticket) {
    function pos() {
      var list = (S.snap && S.snap.positions) || [];
      for (var i = 0; i < list.length; i++) if (list[i].ticket === ticket) return list[i];
      return null;
    }
    var p = pos();
    if (!p) return;

    var node = el(
      '<div>' +
      '<div id="p-head"></div>' +
      '<div class="two-col" style="margin:14px 0 10px">' +
      '<div class="field"><label>' + esc(t("sl")) + '</label>' +
      '<input type="number" id="p-sl" step="any" value="' + (p.sl || "") + '"></div>' +
      '<div class="field"><label>' + esc(t("tp")) + '</label>' +
      '<input type="number" id="p-tp" step="any" value="' + (p.tp || "") + '"></div>' +
      "</div>" +
      '<button class="btn-line" id="p-modify" style="margin-bottom:10px">' +
      esc(t("modify_sltp")) + "</button>" +
      '<button class="btn-line" id="p-half" style="margin-bottom:10px">' +
      esc(t("close_half")) + "</button>" +
      '<button class="btn-line" id="p-chart" style="margin-bottom:10px">' +
      esc(t("show_chart")) + "</button>" +
      '<button class="btn-line danger" id="p-close">' + esc(t("close_position")) + "</button>" +
      "</div>");

    function head() {
      var q = pos();
      if (!q) { closeSheet(); refresh(); return; }
      node.querySelector("#p-head").innerHTML =
        '<div class="acct-label">' + esc(q.symbol) + " · " +
        esc(t(q.type)) + " " + fmt(q.volume, 2) + "</div>" +
        '<div class="acct-equity numeric ' + cls(q.profit) + '">' +
        money(q.profit) + " " + esc(ccy()) + "</div>" +
        '<div class="acct-grid">' +
        kv(t("open_price"), fmt(q.price_open, q.digits)) +
        kv(t("current_price"), fmt(q.price_current, q.digits)) +
        kv(t("swap"), money(q.swap)) +
        kv(t("ticket"), q.ticket) +
        "</div>";
    }

    node.querySelector("#p-modify").onclick = function () {
      api("/api/modify", {
        ticket: ticket,
        sl: parseFloat(node.querySelector("#p-sl").value) || 0,
        tp: parseFloat(node.querySelector("#p-tp").value) || 0,
      }, "POST").then(function () {
        toast(t("modified_ok"), "ok"); refresh();
      }).catch(function (e) { toast(e.message, "err"); });
    };
    node.querySelector("#p-half").onclick = function () {
      var q = pos();
      api("/api/close", { ticket: ticket, volume: q.volume / 2 }, "POST")
        .then(function () { toast(t("closed_ok"), "ok"); closeSheet(); refresh(); })
        .catch(function (e) { toast(e.message, "err"); });
    };
    node.querySelector("#p-chart").onclick = function () {
      var q = pos();
      closeSheet();
      setChartSymbol(q.symbol);
      switchView("chart");
    };
    node.querySelector("#p-close").onclick = function () {
      api("/api/close", { ticket: ticket }, "POST")
        .then(function () { toast(t("closed_ok"), "ok"); closeSheet(); refresh(); })
        .catch(function (e) { toast(e.message, "err"); });
    };

    openSheet(t("position_actions"), node);
    sheetTick = head;
    head();
  }

  function openCancelSheet(order) {
    var node = el(
      '<div><p style="font-size:15px;line-height:1.8;margin-bottom:16px">' +
      esc(order.symbol) + " · " + esc(order.type.replace("_", " ")) + " " +
      fmt(order.volume, 2) + " @ " + fmt(order.price_open, order.digits) +
      '</p><button class="btn-line danger" id="c-yes">' +
      esc(t("cancel_order")) + "</button></div>");
    node.querySelector("#c-yes").onclick = function () {
      api("/api/cancel", { ticket: order.ticket }, "POST")
        .then(function () { toast(t("cancelled_ok"), "ok"); closeSheet(); refresh(); })
        .catch(function (e) { toast(e.message, "err"); });
    };
    openSheet(t("pending_orders"), node);
  }

  // ------------------------------------------------------------- chart tab
  function setChartSymbol(name) {
    S.chartSymbol = name;
    localStorage.setItem("mt5panel.chartSymbol", name);
    loadCandles();
  }

  function renderChartHead() {
    var s = symbolOf(S.chartSymbol);
    $("chart-symbol").textContent = S.chartSymbol || "—";
    $("chart-last").textContent = s ? fmt(s.bid, s.digits) : "";
    if (s) $("chart-last").className = "last numeric";

    var chips = $("tf-chips");
    if (chips.dataset.lang !== S.lang || !chips.dataset.built) {
      chips.dataset.built = "1";
      chips.dataset.lang = S.lang;
      chips.innerHTML = "";
      TFS.forEach(function (tf) {
        var c = el('<button class="chip">' + tf + "</button>");
        c.onclick = function () {
          S.tf = tf; localStorage.setItem("mt5panel.tf", tf);
          renderChartHead(); loadCandles();
        };
        chips.appendChild(c);
      });
    }
    Array.prototype.forEach.call(chips.children, function (c) {
      c.classList.toggle("active", c.textContent === S.tf);
    });

    var acts = $("chart-actions");
    acts.innerHTML = "";
    var pick = el('<button class="chip">⇄ ' + esc(t("symbol")) + "</button>");
    pick.onclick = function () { chartSymbolPicker(); };
    acts.appendChild(pick);
    var trade = el('<button class="chip" style="background:var(--buy);color:#fff;border-color:var(--buy)">' +
      esc(t("new_order")) + "</button>");
    trade.onclick = function () { newOrderSheet(S.chartSymbol); };
    acts.appendChild(trade);
  }

  function chartSymbolPicker() {
    var node = document.createElement("div");
    ((S.snap && S.snap.symbols) || []).forEach(function (s) {
      var row = el('<button class="row"><div class="grow"><div class="name">' +
        esc(s.symbol) + '</div></div><div class="price numeric">' +
        fmt(s.bid, s.digits) + "</div></button>");
      row.onclick = function () { closeSheet(); setChartSymbol(s.symbol); renderChartHead(); };
      node.appendChild(row);
    });
    openSheet(t("symbol"), node);
  }

  function loadCandles() {
    if (!S.chartSymbol) return;
    api("/api/candles", { symbol: S.chartSymbol, tf: S.tf, count: 160 })
      .then(function (d) { S.candles = d.candles; drawChart(); })
      .catch(function (e) { toast(e.message, "err"); });
  }

  function drawChart() {
    var cv = $("chart");
    if (!cv || !S.candles.length) return;
    var dpr = window.devicePixelRatio || 1;
    var w = cv.clientWidth, h = cv.clientHeight;
    cv.width = w * dpr; cv.height = h * dpr;
    var ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    var css = getComputedStyle(document.documentElement);
    var line = css.getPropertyValue("--line").trim() || "#262d38";
    var ink3 = css.getPropertyValue("--ink-3").trim() || "#5c6673";
    var up = css.getPropertyValue("--up").trim() || "#23c26a";
    var down = css.getPropertyValue("--down").trim() || "#f0533f";

    var padR = 58, padB = 20, padT = 8, padL = 6;
    var bars = S.candles.slice(-120);
    var hi = -Infinity, lo = Infinity;
    bars.forEach(function (b) { hi = Math.max(hi, b.h); lo = Math.min(lo, b.l); });
    var span = (hi - lo) || 1;
    hi += span * 0.06; lo -= span * 0.06; span = hi - lo;

    var plotW = w - padR - padL, plotH = h - padB - padT;
    function y(v) { return padT + (hi - v) / span * plotH; }
    var digits = (symbolOf(S.chartSymbol) || {}).digits;
    if (digits == null) digits = 5;

    // grid + right-hand price scale
    ctx.strokeStyle = line; ctx.fillStyle = ink3;
    ctx.font = "10px monospace"; ctx.textBaseline = "middle";
    ctx.lineWidth = 1;
    for (var i = 0; i <= 4; i++) {
      var val = hi - span * i / 4;
      var yy = Math.round(y(val)) + 0.5;
      ctx.beginPath(); ctx.moveTo(padL, yy); ctx.lineTo(w - padR, yy); ctx.stroke();
      ctx.textAlign = "left";
      ctx.fillText(val.toFixed(digits), w - padR + 6, yy);
    }

    var bw = plotW / bars.length;
    var body = Math.max(1, Math.min(9, bw * 0.62));
    bars.forEach(function (b, idx) {
      var cx = padL + bw * (idx + 0.5);
      var rising = b.c >= b.o;
      ctx.strokeStyle = ctx.fillStyle = rising ? up : down;
      ctx.beginPath();
      ctx.moveTo(Math.round(cx) + 0.5, y(b.h));
      ctx.lineTo(Math.round(cx) + 0.5, y(b.l));
      ctx.stroke();
      var top = y(Math.max(b.o, b.c));
      var bot = y(Math.min(b.o, b.c));
      ctx.fillRect(cx - body / 2, top, body, Math.max(1, bot - top));
    });

    // last price marker
    var last = bars[bars.length - 1];
    ctx.strokeStyle = ink3;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padL, Math.round(y(last.c)) + 0.5);
    ctx.lineTo(w - padR, Math.round(y(last.c)) + 0.5);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = last.c >= last.o ? up : down;
    ctx.fillRect(w - padR + 2, y(last.c) - 8, padR - 4, 16);
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.fillText(last.c.toFixed(digits), w - padR / 2, y(last.c));

    // open positions on this symbol
    ((S.snap && S.snap.positions) || []).forEach(function (p) {
      if (p.symbol !== S.chartSymbol) return;
      ctx.strokeStyle = p.type === "buy" ? "#2f81f7" : "#f0533f";
      ctx.setLineDash([2, 3]);
      ctx.beginPath();
      ctx.moveTo(padL, Math.round(y(p.price_open)) + 0.5);
      ctx.lineTo(w - padR, Math.round(y(p.price_open)) + 0.5);
      ctx.stroke();
      ctx.setLineDash([]);
    });
  }

  // ---------------------------------------------------------------- polling
  var pollTimer = null;
  function refresh() {
    return api("/api/snapshot").then(function (d) {
      S.snap = d;
      S.lastError = "";
      if (!S.status || !S.status.connected) {
        return api("/api/status").then(function (st) { S.status = st; renderCurrentView(); });
      }
      S.status.account = d.account;
      if (!S.chartSymbol && d.symbols.length) S.chartSymbol = d.symbols[0].symbol;
      renderCurrentView();
    }).catch(function (e) {
      S.lastError = e.message;
      if (S.status) S.status.connected = false;
      renderTopbar();
    });
  }

  function restartPolling() {
    clearInterval(pollTimer);
    pollTimer = setInterval(function () {
      if (document.hidden || S.busy) return;
      refresh();
      if (S.view === "chart") {
        // refresh the last bar without refetching the whole series every tick
        var s = symbolOf(S.chartSymbol);
        if (s && S.candles.length) {
          var last = S.candles[S.candles.length - 1];
          last.c = s.bid;
          last.h = Math.max(last.h, s.bid);
          last.l = Math.min(last.l, s.bid);
          drawChart();
        }
      }
    }, S.refresh);
  }

  function loadHistory() {
    return api("/api/history", { days: S.historyDays })
      .then(function (d) { S.history = d; renderHistory(); })
      .catch(function (e) { toast(e.message, "err"); });
  }

  // -------------------------------------------------------------- language
  function setLang(lang) {
    S.lang = lang;
    localStorage.setItem("mt5panel.lang", lang);
    var dir = t("_dir");
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
    document.body.dir = dir;
    renderStaticText();
    $("tf-chips").dataset.lang = "";
    renderCurrentView();
    if (S.view === "chart") { renderChartHead(); drawChart(); }
  }

  function switchView(name) {
    S.view = name;
    document.querySelectorAll(".view").forEach(function (v) {
      v.classList.toggle("active", v.id === "view-" + name);
    });
    document.querySelectorAll(".tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.view === name);
    });
    $("fab").style.display = (name === "quotes" || name === "trade") ? "" : "none";
    if (name === "history" && !S.history) loadHistory();
    if (name === "chart") {
      renderChartHead();
      if (!S.candles.length) loadCandles(); else drawChart();
    }
    renderCurrentView();
  }

  // ------------------------------------------------------------------ boot
  function boot() {
    document.documentElement.setAttribute("data-theme", S.theme);
    document.body.classList.toggle("wide", S.wide);
    setLang(S.lang);

    document.querySelectorAll(".tab").forEach(function (b) {
      b.onclick = function () { switchView(b.dataset.view); };
    });
    $("btn-lang").onclick = function () { setLang(S.lang === "ar" ? "en" : "ar"); };
    $("btn-refresh").onclick = function () {
      refresh(); if (S.view === "chart") loadCandles();
      if (S.view === "history") loadHistory();
    };
    $("fab").onclick = function () { newOrderSheet(S.chartSymbol); };
    $("sheet-close").onclick = closeSheet;
    $("scrim").onclick = closeSheet;
    $("btn-close-all").onclick = function () {
      confirmAction(t("close_all_confirm"), function () {
        api("/api/close_all", {}, "POST")
          .then(function () { toast(t("closed_ok"), "ok"); refresh(); })
          .catch(function (e) { toast(e.message, "err"); });
      });
    };
    window.addEventListener("resize", function () {
      if (S.view === "chart") drawChart();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSheet();
    });

    api("/api/status").then(function (st) {
      S.status = st;
      if (!st.connected) toast(t("offline_hint"), "err");
    }).catch(function (e) {
      S.lastError = e.message;
      toast(t("offline_hint"), "err");
    }).then(function () {
      refresh().then(function () {
        if (!S.chartSymbol && S.snap && S.snap.symbols.length) {
          S.chartSymbol = S.snap.symbols[0].symbol;
        }
        switchView("quotes");
      });
      restartPolling();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
