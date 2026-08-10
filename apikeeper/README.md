# مفاتيحي — API Keeper

مساعد يفتح لك الصفحات الرسمية للحصول على مفاتيح API، وينظّم مفاتيحك في مكان
واحد على جهازك. تختارين الخدمة، يوريك الخطوات بالترتيب مع أزرار تفتح كل صفحة،
تسجّلين وتاخذين المفتاح بنفسك، ويحفظه لك مع حالته.

*A concierge for getting API keys: pick a service, it opens the official pages
in order and walks you through, you sign in and grab the key, and it keeps your
keys organized on your device.*

<div dir="rtl">

## كيف تستخدمينها

1. افتحي `index.html` (بالنقر عليه، أو من الرابط المنشور على جوالك).
2. اختاري الخدمة من قائمة المزوّدين، أو ابحثي عنها.
3. اتبعي الخطوات — كل خطوة فيها زر **«افتحي الصفحة»** يوديك للمكان الصح.
4. بعد ما تاخذين المفتاح، الصقيه في الحقل واحفظيه في «مفاتيحي».
5. حدّدي الحالة: لم أطلبه / بانتظار الموافقة / فعّال — عشان تتابعين الطلبات الطويلة.

## المزوّدون الجاهزون

ذكاء اصطناعي (OpenAI، Anthropic، Google Gemini) · تواصل (Pinterest، X،
Meta، Discord، Reddit) · مطوّرون (GitHub، Google Cloud، Stripe) · مراسلة
(Telegram، Twilio) · وسائط (Unsplash) · بيانات (NewsAPI، Alpha Vantage).

**خدمة مو بالقائمة؟** من زر ⋯ اختاري «مزوّد مخصّص»، واكتبي اسمها ورابط صفحة
مفاتيحها والحقول اللي تبين تحفظينها.

## الخصوصية

- **كل مفاتيحك تُحفظ في متصفحك على هذا الجهاز فقط** (localStorage) — ما تُرسل
  لأي سيرفر، ولا حتى لي.
- الأداة ما تسجّل دخولك ولا تلمس حساباتك — بس تفتح لك الصفحات الرسمية، وأنتِ
  تسجّلين على موقع المزوّد مباشرة.
- من زر ⋯ تقدرين **تصدّرين** مفاتيحك كملف (لنقلها لجهاز ثاني أو نسخة احتياطية)
  و**تستوردينها**. احفظي الملف في مكان آمن — يحتوي مفاتيحك بصيغة واضحة.
- المفاتيح تنمسح لو مسحتِ بيانات المتصفح. خذي تصدير احتياطي كل فترة.

## ملف واحد فقط

`index.html` مستقل بالكامل — بدون خادم، بدون تثبيت، بدون إنترنت (عدا فتح صفحات
المزوّدين طبعاً). يشتغل من الكمبيوتر أو الجوال. تقدرين «إضافته للشاشة الرئيسية»
في الجوال ليصير شكله تطبيق.

</div>

---

## English

A single self-contained `index.html`: no server, no install, works offline
(except opening the providers' own pages). Pick a service, follow the ordered
steps with one-tap buttons to each official page, sign in and obtain the key
yourself, then save it with a status (not requested / pending review / active)
so long approvals are easy to track.

Includes curated recipes for ~16 popular providers across AI, social, developer,
messaging, media and data, plus a **custom provider** option for anything else —
name, key-page URL, and the fields you want to store.

**Privacy:** keys live only in this browser's localStorage — nothing is sent
anywhere. Export/import is available for backup and moving between devices; the
export file holds your keys in clear text, so keep it somewhere safe.
