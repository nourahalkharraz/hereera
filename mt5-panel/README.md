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
| **السجل** | الصفقات المغلقة خلال اليوم/الأسبوع/الشهر/٣ شهور، مع صافي الربح ونسبة الصفقات الرابحة ومعامل الربح وأفضل وأسوأ صفقة. |
| **الإعدادات** | اللغة (عربي/إنجليزي)، الثيم (غامق/فاتح)، عرض الواجهة (جوال/واسع)، سرعة التحديث، وبيانات الاتصال. |

**حاسبة المخاطرة**: داخل شاشة الأمر الجديد — تكتبين نسبة المخاطرة من رصيدك
ومسافة وقف الخسارة بالنقاط، وهي تحسب لك حجم اللوت المناسب.

**وقف الخسارة والهدف**: تقدرين تكتبينها **بالنقاط** (المسافة من سعر الدخول)
أو **بالسعر** مباشرة — الزر الصغير جنب العنوان يبدّل بين الطريقتين.

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
