# الاختبارات

تحتاج Node مع `playwright`، وChromium (في بيئة Claude السحابية: `/opt/pw-browsers/chromium`)، وPython مع Pillow وnumpy.

## تشغيل الدعوة محليًا
```bash
cd src && python3 -m http.server 8770
```
ثم افتحي http://127.0.0.1:8770/index.html

## فحص الجودة الكامل
```bash
QA_BASE=http://127.0.0.1:8770/index.html QA_OUT=qa-out node tests/qa.js
```
يجرّب أربعة مقاسات وتقليل الحركة: الأخطاء، الملفات المفقودة، التمرير الأفقي، التدفق كاملًا، نموذج الحضور، الأزرار، الإنجليزي. النتائج في `qa-out/qa.json` مع لقطات.

## روابط قائمة الأقسام (لمس حقيقي)
```bash
QA_BASE=http://127.0.0.1:8770/index.html node tests/qanav.js
```

## مقارنة الداخل بالبكسل قبل التسليم
ضعي النسخة المعتمدة بجانب الجديدة في نفس المجلد (مثلًا `src/approved.html`)، ثم:
```bash
OLD_URL=http://127.0.0.1:8770/approved.html NEW_URL=http://127.0.0.1:8770/index.html OUT=diff-out node tests/innerdiff.js
python3 tests/innerdiff_compare.py diff-out
```
أي فرق خارج ما طُلب يُرجَع.

**ضجيج معروف:** مقارنة الملف بنفسه على مقاس الكمبيوتر قد تُظهر عشرات البكسلات المتفرقة بفرق أقصاه نحو ١٥ (رسم المتصفح غير ثابت تمامًا). هذا ليس تغييرًا. الفرق الحقيقي يظهر كمنطقة متصلة أو بفرق أكبر.
