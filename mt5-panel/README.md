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

### كلمة «ديمو» لها معنيين — انتبهي للفرق

| | الأسعار | الفلوس | تحتاج MT5؟ |
|---|---|---|---|
| **حساب ديمو من الوسيط** ← هذا اللي تبينه | حقيقية ١٠٠٪ | افتراضية | نعم |
| `PREVIEW-fake-prices.bat` | **مولّدة بالبرنامج** | افتراضية | لا |

**حساب الديمو من الوسيط** هو حساب MT5 كامل: نفس أسعار الذهب اللحظية، نفس
السبريد، نفس تنفيذ الأوامر ورفضها — الفرق الوحيد إن الفلوس مو حقيقية. اللوحة
ما تفرّق بينه وبين الحساب الحقيقي، تشتغل معه بالكامل وبدون أي تعديل: افتحي MT5،
سجّلي دخول بحساب الديمو، وشغّلي `START.bat` العادي. **هذي هي الطريقة الصح
للتجربة.**

كيف تفتحين حساب ديمو (دقيقتين): سجّلي في أي وسيط تثقين فيه واطلبي حساب تجريبي،
بيعطونك رقم حساب وكلمة سر واسم سيرفر، تدخلينهم في MT5 من
`File ← Login to Trade Account`. اختاري وسيط سبريد الذهب عنده قريب من اللي
بتتداولين عليه فعلاً — لأن السبريد هو أهم عامل في السكالبينج.

**وضع الأسعار الوهمية** (`PREVIEW-fake-prices.bat` أو `--demo`) غرضه الوحيد إنك
تشوفين شكل الواجهة وقت ما يكون MT5 مو متاح. الأسعار فيه مخترعة وما تمثّل السوق،
فلا تحكمين على النظام من نتائجه.

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

مضبوط افتراضياً على **سكالبينج الذهب (XAUUSD)**: دخول على فريم M5 داخل اتجاه
M15. زر واحد كبير للتشغيل والإيقاف.

### كيف يقرر — وليش يمتنع

قبل ما يفكر في أي صفقة، لازم يعدّي أربع بوابات، وأي وحدة تفشل = ما فيه دخول:

1. **الوقت.** يتداول فقط في نافذة لندن–نيويورك (٠٧:٠٠–٢٠:٣٠ بتوقيت UTC)،
   ويمتنع في وقت التبييت (٢٠:٤٥–٢٣:٥٩) لأن السبريد يتوسّع فيه، وفي عطلة
   نهاية الأسبوع. كل هالأوقات تعدّلينها من التبويب.
2. **التكلفة — وهذي أهم وحدة في السكالبينج.** لو السبريد أوسع من ٢٥٪ من متوسط
   حركة الشمعة، أو الهدف أقل من ٥ أضعاف السبريد، يرفض الصفقة. صفقة صح فنياً
   وسبريدها واسع = صفقة خاسرة. فيه كمان حد أقصى صريح للسبريد بالنقاط.
3. **حالة التقلب.** لو السوق أهدأ من ٦٥٪ من معدله = بلا حركة. ولو أعلى من
   ٢٢٠٪ = غالباً خبر اقتصادي، والدخول فيه قمار. يمتنع في الحالتين.
4. **اتجاه الفريم الأكبر.** لو متردد، ما فيه صفقة.

بعدها **ثمانية فحوصات** بأوزان مجموعها ١٠٠:

| الفحص | الوزن |
|---|---|
| الاتجاه متوافق على فريم الدخول | ١٨ |
| الزخم يتزايد (MACD) | ١٦ |
| قوة الاتجاه ADX واتجاهه يوافق (ADX ≥ ٢٠) | ١٤ |
| السعر بصف الاتجاه | ١٢ |
| RSI في نطاق صحي (مو متشبّع) | ١٢ |
| الشمعة الأخيرة تؤكد بجسم حقيقي | ١٠ |
| الدخول مو متأخر عن الحركة | ١٠ |
| المتوسط يلتف للاتجاه | ٨ |

المجموع = **درجة الثقة**، وما يدخل إلا فوق ٧٢٪. وفي التبويب تشوفين لكل رمز
درجته والفحوصات اللي نجحت (أخضر) واللي فشلت (أحمر).

**الوقف والهدف**: الوقف يتحط خلف آخر قاع/قمة حقيقية (مو رقم ثابت) وبحدود
٠.٧–١.٦ من متوسط المدى، والهدف يتعدّل عشان العائد يبقى ١.٥ ضعف المخاطرة على
الأقل مهما كان الوقف.

### إدارة الصفقة بعد الدخول

هذا اللي يفرق فعلياً في السكالبينج:

- عند ربح **1R**: يقفل **نص الصفقة** ويحوّل الوقف للتعادل — الباقي مجاني.
- بعد **1.3R**: يتبع السعر بوقف متحرك على مسافة متوسط مدى واحد.

### الحدود

| الحد | الافتراضي |
|---|---|
| المخاطرة لكل صفقة | ٠.٥٪ من الرصيد |
| أقصى صفقات مفتوحة | ١ |
| أقصى صفقات باليوم | ٥ |
| حد الخسارة اليومي | ٢٪ — يوقف الروبوت لبقية اليوم |
| أقصى خسائر متتالية | ٣ — يوقف الروبوت |
| انتظار بعد كل صفقة | ١٥ دقيقة لنفس الرمز |
| أقصى سبريد | ٤٥ نقطة |
| أقصى انزلاق | ١٥ نقطة |

### الباك تست — جربيه على التاريخ قبل أي شي

في نفس التبويب: تحددين عدد الشموع والسبريد المفترض، وتضغطين «شغّلي الباك تست».
يعيد تشغيل **نفس** المنطق و**نفس** إدارة الصفقة على تاريخ الذهب الحقيقي من
حسابك، ويعطيك: عدد الصفقات، نسبة الربح، معامل الربح، صافي الربح ٪، أقصى تراجع،
التوقع لكل صفقة بالـ R، أطول سلسلة خسائر، ومنحنى رأس المال — وكمان أكثر أسباب
الامتناع، عشان تعرفين لو الفلاتر متشددة زيادة.

**حدود الباك تست** (مهمة): يفترض سبريد ثابت وما يحسب العمولة ولا الانزلاق،
ولما تلمس الشمعة الوقف والهدف مع بعض يفترض إن الوقف ضرب أول. يعني النتيجة
الحقيقية غالباً أسوأ من اللي تشوفينها.

### الخطة اللي أنصح فيها

1. **باك تست** على ٥٠٠٠ شمعة بسبريد حقيقي من وسيطك (شوفيه في تبويب الأسعار).
2. لو التوقع لكل صفقة موجب ومعامل الربح فوق ١.٣ — **محاكاة** أسبوع كامل على
   حساب حقيقي مفتوح (بدون تنفيذ)، وقارني نتيجة المحاكاة بالباك تست.
3. لو الاثنين متقاربين — **حساب ديمو حقيقي** من وسيطك أسبوعين بوضع «حقيقي».
   هنا تظهر الأشياء اللي ما يشوفها الباك تست: الانزلاق، رفض الأوامر، توسّع
   السبريد وقت الأخبار.
4. بعدها فقط، حساب حقيقي بأصغر مبلغ تتحملين خسارته كامل، وبمخاطرة ٠.٢٥٪.

> ما فيه تركيبة مؤشرات تضمن نجاح الصفقات. اللي فوق يخلي الاحتمالات في صفك
> ويحدّد الخسارة، لكن السوق ممكن يعطيك أسبوع خاسر مهما كان النظام حلو.

## الأمان

- الخادم يستمع على `127.0.0.1` فقط — ما ينفتح على الشبكة ولا على الإنترنت.
- كل طلب لازم يحمل مفتاح يتولّد من جديد في كل تشغيل، وموجود في الرابط اللي
  ينفتح لك. يعني ولا موقع ولا برنامج ثاني على جهازك يقدر يرسل أوامر للوحة.
- ما فيه أي إرسال لأي سيرفر خارجي — بيانات حسابك تبقى عندك.
- ما يحتاج كلمة سر حسابك: يتصل بالترمنال المفتوح أصلاً.
- **الأوامر حقيقية.** أي شراء أو بيع أو إغلاق من اللوحة ينفّذ فعلياً على حسابك.
  جرّبي على حساب تجريبي (demo) أول، وكل أمر فيه شاشة تأكيد قبل التنفيذ.

## الدخول من الجوال

اللوحة تشتغل على الكمبيوتر اللي في البيت، وتفتحينها من جوالك بالمتصفح.

### الطريقة الآمنة: شبكة خاصة (Tailscale)

تخلّي الكمبيوتر والجوال كأنهم على نفس الشبكة، بدون ما تفتحين أي منفذ للإنترنت.
مجاني للاستخدام الشخصي:

1. ثبّتي **Tailscale** على الكمبيوتر وعلى الجوال، وسجّلي دخول بنفس الحساب في
   الاثنين.
2. على الكمبيوتر: عدّلي كلمة السر داخل `START-PHONE.bat` وشغّليه.
3. من تطبيق Tailscale على الجوال خذي عنوان الكمبيوتر (مثل `100.x.y.z`)،
   وافتحي في متصفح الجوال: `http://100.x.y.z:8777`
4. أدخلي كلمة السر. من قائمة المتصفح اختاري **«إضافة إلى الشاشة الرئيسية»**
   وبيصير شكله تطبيق كامل الشاشة.

بدون Tailscale وأنتِ بنفس شبكة البيت (واي فاي واحد) نفس الشي، بس تستخدمين
عنوان الكمبيوتر المحلي (`192.168.x.x`) — وهذي تنفع في البيت فقط.

### الأمان في وضع الجوال

- كلمة سر إجبارية، وبعد ٥ محاولات غلط يتقفل الدخول ٥ دقائق.
- الجلسة تنتهي بعد ١٢ ساعة.
- الصفحة ما تعطي مفتاح الدخول لأي جهاز — المفتاح موجود فقط في الرابط اللي
  ينفتح على الكمبيوتر نفسه.
- الطلبات من مواقع ثانية مرفوضة.

> **لا تعملين port forwarding من الراوتر ولا تحطينها على عنوان عام.** لوحة
> تفتح صفقات على حسابك ومعرّضة للإنترنت المفتوح فكرة سيئة مهما كانت كلمة السر
> قوية. Tailscale (أو شبكة خاصة مثلها) هي الطريقة الصح.
>
> ولو تبين تراقبين بس بدون أي مخاطرة: شغّليها بـ `--read-only` وما راح يقدر
> أحد يفتح ولا يقفل أي صفقة منها.

## لو ما اشتغلت

| المشكلة | الحل |
|---|---|
| `initialize() failed` | افتحي MT5 وسجّلي الدخول أول، وبعدين شغّلي السكربت. لو الترمنال مثبّت بمكان غير معتاد: `python server.py --terminal "C:/…/terminal64.exe"` |
| `MetaTrader5 package is not installed` | `pip install MetaTrader5` — تنبيه: المكتبة تشتغل على **ويندوز** فقط. |
| اللوحة تفتح لكن مكتوب «غير متصل» | تأكدي إن نافذة الترمنال ما انسكرت، وإن «التداول الآلي» مو معطّل من إعدادات MT5. |
| الأمر ينرفض | غالباً السبب من الوسيط: السوق مقفل، أو اللوت أصغر/أكبر من المسموح، أو وقف الخسارة قريب من السعر أكثر من اللازم. نص رسالة الوسيط يظهر لك في التنبيه. |
| البورت مشغول | `python server.py --port 8900` |
| الباك تست يقول «ما فيه تاريخ كافي» | افتحي شارت الذهب في MT5 على نفس الفريم ونزلي للأسفل شوي عشان الترمنال يحمّل التاريخ، وبعدين أعيدي الباك تست. |
| الروبوت شغال بس ما يفتح ولا صفقة | طبيعي — أغلب الوقت الفلاتر ترفض. شوفي «قراءة السوق الآن» و«أكثر أسباب الامتناع» في الباك تست. لو السبب دايماً «خارج وقت التداول» عدّلي الأوقات (كلها UTC). |

</div>

---

## English

A small local web app that mirrors the MetaTrader 5 **mobile** layout on a
desktop, for people who find the MT5 desktop terminal hard to navigate.

### "Demo" means two different things

A **broker demo account** is a full MT5 account — real gold prices, real
spreads, real order execution and rejection — with virtual money. The panel
treats it exactly like a live account and needs no special mode: log into it in
MT5 and run `START.bat`. That is the right way to test.

`--demo` / `PREVIEW-fake-prices.bat` is something else entirely: prices
invented by the script, so the interface can be looked at with no terminal
running. Never judge the strategy by what happens there.

### Run

1. Open MetaTrader 5 and log in (a broker demo account is fine — and is where
   you should start). Leave it running.
2. Double-click `START.bat` (or `pip install MetaTrader5 && python server.py --open`).
3. The browser opens the panel at `http://127.0.0.1:8777`.

Flags: `--demo` (fake prices, no terminal needed), `--read-only` (no trading),
`--port N`, `--terminal <path to terminal64.exe>`, `--open`.

### Automatic trading

The **Auto** tab runs a signal engine on a timer and can open trades on its
own. It ships configured for **XAUUSD scalping**: M5 entries inside the M15
trend.

Four gates come before any analysis — trading session (London/NY by default,
with a rollover blackout and no weekends), **cost** (the spread must stay under
25% of one ATR and the target must clear 5x the spread; on gold this rejects
more setups than every indicator combined), volatility regime (too quiet drifts,
too wild is a news release), and higher-timeframe direction. Then eight
weighted checks score the setup out of 100: entry-trend agreement (18), MACD
momentum (16), ADX strength with directional agreement (14), price side (12),
RSI band (12), last-candle confirmation (10), not overextended (10), and
moving-average slope (8). It enters above your confidence threshold, default 72.

Stops sit behind the last real swing rather than at a fixed multiple, clamped
to 0.7–1.6 ATR, and the target scales so reward stays at least 1.5x the risk
actually taken. Open trades are then managed: half off and stop to break-even
at 1R, ATR trail after 1.3R.

Risk manager: size from a risk percentage (0.5% default), mandatory stop, one
open trade, five a day, a 2% daily loss limit and a three-loss streak brake
that both halt the engine until tomorrow, a per-symbol cooldown, a hard spread
cap and a slippage cap. Daily counters survive a restart.

### Backtest

The same tab replays the **same** entry logic and the **same** trade management
over your broker's real history and reports trade count, win rate, profit
factor, net %, max drawdown, expectancy in R, longest losing streak, an equity
curve, and the most common reasons setups were skipped.

It assumes a fixed spread, ignores commission and slippage, and resolves a
candle that touches both stop and target as a loss. Real results are usually
worse. Treat a good curve as permission to run it on paper, not to go live.

### Using it from your phone

`START-PHONE.bat` (or `python server.py --lan --password "..."`) makes the panel
reachable from other devices. Put the PC and the phone on a **private network**
— Tailscale is the easy one — and open `http://<pc-address>:8777` on the phone,
then "Add to Home Screen" for a full-screen app.

Off-machine access requires a password, locks out for 5 minutes after 5 wrong
attempts, expires sessions after 12 hours, refuses cross-site requests, and
never serves the launch key to a remote device.

**Do not port-forward this to the open internet.** A panel that can open
positions on your account should not be exposed publicly, whatever the
password. Run it with `--read-only` if you only want to watch from outside.

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
strategy.py       indicators, filters and the weighted signal engine
autotrader.py     the engine loop, risk manager, trade management, paper mode
backtest.py       historical replay of the same logic, as a background job
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

By default the socket binds to `127.0.0.1`, `Host`/`Origin` are checked, and
every API call must carry a key regenerated at each start and handed to you in
the launch URL — so no other page or program on the machine can drive the
panel. With `--lan`, a password and 12-hour sessions are added on top, and the
served page never contains the key. Nothing is sent off the machine either way.

**Orders placed here are real, and the engine can place them without asking.**
Backtest, then paper, then a broker demo account, then real money — in that
order.
