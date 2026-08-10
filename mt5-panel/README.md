# MT5 Panel — واجهة الجوال على الكمبيوتر

لوحة محلية تشتغل على جهازك وتتصل بترمنال **MetaTrader 5** المفتوح عندك، وتعطيك
نفس تجربة تطبيق الجوال: تبويبات أسفل الشاشة، أزرار كبيرة، شراء/بيع بضغطة، وكل
شي بالعربي أو الإنجليزي بزر تبديل واحد.

*A local, phone-style front end for the MetaTrader 5 desktop terminal.
Arabic / English, RTL-aware. Scroll down for the English section.*

<div dir="rtl">

## التشغيل بثلاث خطوات

1. **افتحي MetaTrader 5** على الكمبيوتر وسجّلي الدخول في حسابك، وخلّيه مفتوح.
2. **اضغطي مرتين على `START.bat`** — أول مرة بيثبّت المكتبة المطلوبة لحاله
   (يحتاج بايثون مثبّت على الجهاز؛ لو مو مثبّت حمّليه من python.org واختاري
   «Add Python to PATH» أثناء التثبيت).
3. المتصفح بينفتح تلقائياً على اللوحة. خلاص.

بدل الـ `.bat` تقدرين تشغّلينه من الترمنال:

```
pip install MetaTrader5
python server.py --open
```

### تبين تجربينها قبل ما تربطينها بحسابك؟

```
python server.py --demo --open
```

يشغّل اللوحة بأسعار وهمية وحساب وهمي، بدون أي اتصال بـ MT5 وبدون أي أمر حقيقي.
مناسب عشان تتعوّدين على الواجهة أول.

### وضع العرض فقط (بدون تداول)

```
python server.py --read-only
```

يعطّل كل أوامر الشراء والبيع والإغلاق والتعديل — عرض فقط.

## وش تسوي اللوحة

| التبويب | المحتوى |
|---|---|
| **الأسعار** | قائمة المتابعة بأسعار حيّة (بيع/شراء + السبريد)، وإضافة أو حذف رموز بالبحث. الضغط على أي رمز يفتح شاشة أمر جديد. |
| **الرسم** | شموع يابانية مع اختيار الفريم (M1 → W1)، وخط يوضّح سعر فتح صفقاتك على نفس الرمز. |
| **التداول** | ملخص الحساب (صافي رأس المال، الرصيد، الربح العائم، الهامش)، الصفقات المفتوحة بأرباحها اللحظية، والأوامر المعلّقة. الضغط على أي صفقة يفتح: إغلاق، إغلاق نصف، تعديل الوقف والهدف، عرض الرسم. |
| **الروبوت** | التداول الآلي: زر تشغيل/إيقاف، درجة الثقة لكل رمز مع سبب القرار، حدود المخاطرة، وسجل القرارات. تفاصيله تحت. |
| **السجل** | الصفقات المغلقة خلال اليوم/الأسبوع/الشهر/٣ شهور، مع صافي الربح ونسبة الصفقات الرابحة ومعامل الربح وأفضل وأسوأ صفقة. |
| **الإعدادات** | اللغة (عربي/إنجليزي)، الثيم (غامق/فاتح)، عرض الواجهة (جوال/واسع)، سرعة التحديث، وبيانات الاتصال. |

**حاسبة المخاطرة**: داخل شاشة الأمر الجديد — تكتبين نسبة المخاطرة من رصيدك
ومسافة وقف الخسارة بالنقاط، وهي تحسب لك حجم اللوت المناسب.

**وقف الخسارة والهدف**: تقدرين تكتبينها **بالنقاط** (المسافة من سعر الدخول)
أو **بالسعر** مباشرة — الزر الصغير جنب العنوان يبدّل بين الطريقتين.

## تبويب «الروبوت» — التداول الآلي

محرّك يدرس السوق كل ٢٠ ثانية ويفتح صفقة لحاله لما تتفق المؤشرات. زر واحد
كبير للتشغيل والإيقاف.

### كيف يقرر

يمشي على ثلاث مراحل، ولو فشلت أي مرحلة ما يدخل:

1. **هل السوق قابل للتداول أصلاً؟** يرفض إذا كان السبريد واسع مقارنة بحركة
   السوق (أكثر من ١٥٪ من متوسط المدى الحقيقي)، أو إذا كان السوق هادي أكثر من
   اللازم.
2. **وش اتجاه الفريم الأكبر؟** (H1 افتراضياً) — متوسط ٥٠ فوق متوسط ٢٠٠ والسعر
   فوقهم = اتجاه صاعد، والعكس هابط. لو الفريم الأكبر متردد، ما فيه صفقة.
3. **ست فحوصات على فريم الدخول** (M15 افتراضياً)، لكل وحدة وزن ومجموعها ١٠٠:
   توافق الاتجاه (٢٥) · السعر بصف الاتجاه (١٥) · الزخم يتزايد بالـ MACD (٢٠) ·
   RSI في نطاق صحي مو متشبّع (٢٠) · المتوسط يلتف للاتجاه (١٠) · الدخول مو
   متأخر عن الحركة (١٠).

المجموع = **درجة الثقة**. ما يدخل إلا إذا تجاوزت الحد اللي تحددينه (٧٠٪
افتراضياً). وفي التبويب تشوفين لكل رمز درجته والفحوصات اللي نجحت (أخضر) واللي
فشلت (أحمر) — يعني تعرفين بالضبط ليش دخل أو ليش امتنع.

وقف الخسارة = ١.٥ × متوسط المدى الحقيقي، والهدف = ٢.٥ × — يعني الربح المتوقع
أكبر من الخسارة المحتملة بنسبة ١.٦٧ تقريباً.

### الحدود (تتغير من نفس التبويب)

| الحد | الافتراضي |
|---|---|
| المخاطرة لكل صفقة | ٠.٥٪ من الرصيد — وحجم اللوت يتحسب منها |
| أقصى صفقات مفتوحة | ١ |
| أقصى صفقات باليوم | ٣ |
| حد الخسارة اليومي | ٢٪ — يوقف الروبوت لبقية اليوم |
| فترة انتظار بعد كل صفقة | ٦٠ دقيقة لنفس الرمز |
| أقل ثقة للدخول | ٧٠٪ |

فوق هذا: كل صفقة لها وقف خسارة إجباري، وما يفتح صفقة على رمز فيه صفقة مفتوحة
(لا منه ولا منك)، والحدود اليومية محفوظة على القرص فما تنمسح لو أغلقتي البرنامج
وفتحتيه.

### يبدأ في وضع المحاكاة

الروبوت يبدأ على **«محاكاة»**: يعطي الإشارات ويتابعها بأسعار حقيقية ويحسب
أرباحها وخسائرها، **بدون ما يرسل أي أمر للوسيط**. شغّليه أسبوع على المحاكاة
وشوفي النتيجة في «سجل القرارات» قبل ما تحولينه لـ «حقيقي» (وفيه شاشة تأكيد
قبل التحويل).

> بصراحة: هذا محرّك قواعد فنية شفاف، مو تنبؤ بالمستقبل. المؤشرات تصف اللي صار،
> والسوق يتغيّر. ممكن يمر عليه أيام خاسرة. الحدود أعلاه موجودة عشان الخسارة
> تبقى محدودة، مو عشان تختفي. لا تشغّلينه على فلوس ما تتحملين خسارتها.

## الأمان

- الخادم يستمع على `127.0.0.1` فقط — ما ينفتح على الشبكة ولا على الإنترنت.
- كل طلب لازم يحمل مفتاح يتولّد من جديد في كل تشغيل، وموجود في الرابط اللي
  ينفتح لك. يعني ولا موقع ولا برنامج ثاني على جهازك يقدر يرسل أوامر للوحة.
- ما فيه أي إرسال لأي سيرفر خارجي — بيانات حسابك تبقى عندك.
- ما يحتاج كلمة سر حسابك: يتصل بالترمنال المفتوح أصلاً.
- **الأوامر حقيقية.** أي شراء أو بيع أو إغلاق من اللوحة ينفّذ فعلياً على حسابك.
  جرّبي على حساب تجريبي (demo) أول، وكل أمر فيه شاشة تأكيد قبل التنفيذ.

## لو ما اشتغلت

| المشكلة | الحل |
|---|---|
| `initialize() failed` | افتحي MT5 وسجّلي الدخول أول، وبعدين شغّلي السكربت. لو الترمنال مثبّت بمكان غير معتاد: `python server.py --terminal "C:/…/terminal64.exe"` |
| `MetaTrader5 package is not installed` | `pip install MetaTrader5` — تنبيه: المكتبة تشتغل على **ويندوز** فقط. |
| اللوحة تفتح لكن مكتوب «غير متصل» | تأكدي إن نافذة الترمنال ما انسكرت، وإن «التداول الآلي» مو معطّل من إعدادات MT5. |
| الأمر ينرفض | غالباً السبب من الوسيط: السوق مقفل، أو اللوت أصغر/أكبر من المسموح، أو وقف الخسارة قريب من السعر أكثر من اللازم. نص رسالة الوسيط يظهر لك في التنبيه. |
| البورت مشغول | `python server.py --port 8900` |

</div>

---

## English

A small local web app that mirrors the MetaTrader 5 **mobile** layout on a
desktop, for people who find the MT5 desktop terminal hard to navigate.

### Run

1. Open MetaTrader 5 and log in. Leave it running.
2. Double-click `START.bat` (or `pip install MetaTrader5 && python server.py --open`).
3. The browser opens the panel at `http://127.0.0.1:8777`.

Flags: `--demo` (fake prices, no terminal needed), `--read-only` (no trading),
`--port N`, `--terminal <path to terminal64.exe>`, `--open`.

### Automatic trading

The **Auto** tab runs a signal engine every 20 seconds and can open trades on
its own. It gates on a higher-timeframe trend, refuses markets where the spread
is wide relative to ATR or volatility has died, then scores six weighted checks
on the entry timeframe (trend agreement, price side, MACD momentum, RSI band,
moving-average slope, and how extended the entry is). It enters only above your
confidence threshold, and the tab shows which checks passed and which failed
for every symbol, so each decision is inspectable.

Risk manager, all editable in the tab: position size from a risk percentage
(0.5% default), mandatory ATR-based stop loss, one open trade, three trades a
day, a 2% daily loss limit that halts the engine until tomorrow, and a
per-symbol cooldown. Daily counters survive a restart.

It starts in **paper** mode — signals are tracked against live prices but no
order reaches the broker until you switch to live and confirm. This is a
transparent rule-based engine, not a prediction: it can and will have losing
runs, and the limits exist to bound that, not to remove it.

### Features

Live Market Watch quotes · candlestick chart with M1–W1 timeframes · account
summary · open positions with live P/L, close / partial close / SL-TP edit ·
pending orders · closed-trade history with win rate and profit factor ·
position-size calculator from a risk percentage · Arabic (RTL) and English ·
dark and light themes.

### How it is put together

```
server.py         stdlib HTTP server: routing, loopback + key auth, static files
mt5_bridge.py     every call into the official MetaTrader5 python package
strategy.py       indicators and the weighted signal engine (pure python)
autotrader.py     the engine loop, risk manager and paper-trade tracking
demo_bridge.py    same interface, simulated market — used by --demo
web/index.html    layout
web/app.css       phone-shaped, theme- and RTL-aware styling
web/app.js        views, order flow, canvas chart, polling
web/i18n.js       Arabic + English strings
```

The only dependency is `MetaTrader5` (Windows only, since that is where the
terminal runs). Everything else is the python standard library and plain
browser JavaScript — no build step, no npm, no CDN.

### Security model

The socket binds to `127.0.0.1`, the `Host`/`Origin` headers are checked, and
every API call must carry a key regenerated at each start and handed to you in
the launch URL — so no other page or program on the machine can drive the
panel. No data is sent anywhere off the machine.

**Orders placed here are real.** Test on a demo account first.
