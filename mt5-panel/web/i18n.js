/* Arabic / English strings. Switching language also flips the layout to RTL. */

window.I18N = {
  ar: {
    _dir: "rtl", _lang: "ar", _other: "EN",
    app_title: "لوحة MT5",
    tab_quotes: "الأسعار", tab_chart: "الرسم", tab_trade: "التداول",
    tab_history: "السجل", tab_settings: "الإعدادات",

    connected: "متصل", disconnected: "غير متصل", demo_mode: "وضع تجريبي (بدون MT5)",
    read_only: "وضع العرض فقط — التداول معطّل",
    connecting: "جارٍ الاتصال…",

    // quotes
    add_symbol: "إضافة رمز", search_symbol: "ابحث عن رمز…",
    no_symbols: "ما فيه رموز في قائمة المتابعة.\nاضغطي «إضافة رمز» لإضافة أول رمز.",
    spread: "السبريد", bid: "بيع", ask: "شراء",
    added: "تمت الإضافة", removed: "تم الحذف",
    remove_symbol: "حذف من القائمة",

    // account
    equity: "صافي رأس المال", balance: "الرصيد", floating_pl: "الربح العائم",
    margin: "الهامش المستخدم", free_margin: "الهامش الحر", margin_level: "مستوى الهامش",
    leverage: "الرافعة", account: "الحساب",

    // positions
    positions: "الصفقات المفتوحة", pending_orders: "الأوامر المعلّقة",
    no_positions: "ما فيه صفقات مفتوحة.",
    no_orders: "ما فيه أوامر معلّقة.",
    close_all: "إغلاق كل الصفقات",
    close_all_confirm: "متأكدة من إغلاق كل الصفقات المفتوحة؟",
    volume: "الحجم (لوت)", open_price: "سعر الفتح", current_price: "السعر الحالي",
    profit: "الربح", swap: "السواب", ticket: "رقم الصفقة",

    // sheets
    new_order: "أمر جديد", symbol: "الرمز", lot: "اللوت",
    sl: "وقف الخسارة", tp: "جني الأرباح",
    sl_tp_hint: "اتركيها فاضية إذا ما تبين وقف خسارة أو جني أرباح.",
    points: "نقطة", price_word: "سعر", by_points: "بالنقاط", by_price: "بالسعر",
    risk_calc: "حاسبة المخاطرة", risk_amount: "المبلغ المخاطر به",
    risk_percent: "نسبة من الرصيد %", calc: "احسبي اللوت",
    calc_result: "اللوت المقترح: {lot} — الخسارة المتوقعة تقريباً {loss}",
    sell: "بيع", buy: "شراء",
    confirm_order: "تأكيد: {side} {vol} لوت من {sym}؟",
    order_done: "تم تنفيذ الأمر ✓", order_failed: "تعذّر تنفيذ الأمر",

    position_actions: "خيارات الصفقة",
    close_position: "إغلاق الصفقة", close_half: "إغلاق نصف الصفقة",
    modify_sltp: "تعديل الوقف والهدف", show_chart: "عرض الرسم البياني",
    closed_ok: "تم إغلاق الصفقة ✓", modified_ok: "تم التعديل ✓",
    cancel_order: "إلغاء الأمر المعلّق", cancelled_ok: "تم إلغاء الأمر ✓",
    save: "حفظ", cancel: "إلغاء",
    confirm_title: "تأكيد", confirm_yes: "تأكيد",

    // history
    today: "اليوم", week: "أسبوع", month: "شهر", months3: "٣ شهور",
    net_profit: "صافي الربح", trades: "عدد الصفقات", win_rate: "نسبة الربح",
    best_trade: "أفضل صفقة", worst_trade: "أسوأ صفقة", profit_factor: "معامل الربح",
    no_history: "ما فيه صفقات مغلقة في هالفترة.",

    // settings
    appearance: "المظهر", connection: "الاتصال", about: "عن الأداة",
    language: "اللغة", theme: "الثيم", dark: "غامق", light: "فاتح",
    width: "عرض الواجهة", phone: "جوال", wide: "واسع",
    refresh_rate: "سرعة التحديث", server: "السيرفر", currency: "العملة",
    terminal: "الترمنال",
    about_text: "لوحة محلية تشتغل على جهازك وتتصل بترمنال MetaTrader 5 المفتوح عندك. كل البيانات تبقى على جهازك ولا تنرسل لأي سيرفر خارجي. الأوامر تنفَّذ فعلياً على حسابك — راجعي كل أمر قبل التأكيد.",

    error: "خطأ", offline_hint: "تأكدي إن ترمنال MT5 مفتوح ومسجّلة الدخول فيه، وإن الخادم شغّال.",
  },

  en: {
    _dir: "ltr", _lang: "en", _other: "ع",
    app_title: "MT5 Panel",
    tab_quotes: "Quotes", tab_chart: "Chart", tab_trade: "Trade",
    tab_history: "History", tab_settings: "Settings",

    connected: "Connected", disconnected: "Disconnected", demo_mode: "Demo mode (no MT5)",
    read_only: "Read-only mode — trading disabled",
    connecting: "Connecting…",

    add_symbol: "Add symbol", search_symbol: "Search a symbol…",
    no_symbols: "No symbols in Market Watch.\nTap “Add symbol” to add your first one.",
    spread: "Spread", bid: "Bid", ask: "Ask",
    added: "Added", removed: "Removed",
    remove_symbol: "Remove from list",

    equity: "Equity", balance: "Balance", floating_pl: "Floating P/L",
    margin: "Margin", free_margin: "Free margin", margin_level: "Margin level",
    leverage: "Leverage", account: "Account",

    positions: "Open positions", pending_orders: "Pending orders",
    no_positions: "No open positions.",
    no_orders: "No pending orders.",
    close_all: "Close all positions",
    close_all_confirm: "Close every open position?",
    volume: "Volume (lots)", open_price: "Open price", current_price: "Current price",
    profit: "Profit", swap: "Swap", ticket: "Ticket",

    new_order: "New order", symbol: "Symbol", lot: "Lots",
    sl: "Stop loss", tp: "Take profit",
    sl_tp_hint: "Leave empty for no stop loss / take profit.",
    points: "points", price_word: "price", by_points: "By points", by_price: "By price",
    risk_calc: "Risk calculator", risk_amount: "Risk amount",
    risk_percent: "Risk % of balance", calc: "Calculate lots",
    calc_result: "Suggested lots: {lot} — estimated loss ≈ {loss}",
    sell: "SELL", buy: "BUY",
    confirm_order: "Confirm: {side} {vol} lots of {sym}?",
    order_done: "Order executed ✓", order_failed: "Order failed",

    position_actions: "Position actions",
    close_position: "Close position", close_half: "Close half",
    modify_sltp: "Modify SL / TP", show_chart: "Open chart",
    closed_ok: "Position closed ✓", modified_ok: "Updated ✓",
    cancel_order: "Cancel pending order", cancelled_ok: "Order cancelled ✓",
    save: "Save", cancel: "Cancel",
    confirm_title: "Confirm", confirm_yes: "Confirm",

    today: "Today", week: "Week", month: "Month", months3: "3 months",
    net_profit: "Net profit", trades: "Trades", win_rate: "Win rate",
    best_trade: "Best trade", worst_trade: "Worst trade", profit_factor: "Profit factor",
    no_history: "No closed trades in this period.",

    appearance: "Appearance", connection: "Connection", about: "About",
    language: "Language", theme: "Theme", dark: "Dark", light: "Light",
    width: "Layout width", phone: "Phone", wide: "Wide",
    refresh_rate: "Refresh rate", server: "Server", currency: "Currency",
    terminal: "Terminal",
    about_text: "A local panel that runs on your own PC and talks to the MetaTrader 5 terminal you already have open. Data never leaves this machine. Orders are sent to your real account — review every order before confirming.",

    error: "Error", offline_hint: "Make sure MT5 is open and logged in, and that the server script is running.",
  },
};
