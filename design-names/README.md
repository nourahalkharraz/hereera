# خطوطُ أسماء العروسين — لوحةُ تجربة

الترتيبُ معتمدٌ (اسمٌ، فاصل، اسم) والخطُّ وحدَه محلُّ التجربة.
لم يُطبَّق شيءٌ على `invitation/index.html`.

| الملفّ | الخطّ | العائلة |
|---|---|---|
| `Main.dc.html` | Reem Kufi | المعتمدُ الآن — كوفيٌّ هندسيّ |
| `F-Aref.dc.html` | Aref Ruqaa | رقعةٌ كلاسيكيّة |
| `F-Messiri.dc.html` | El Messiri | حديثٌ بميلٍ يدويّ |
| `F-Amiri.dc.html` | Amiri | نسخٌ كلاسيكيّ |
| `F-Qahiri.dc.html` | Qahiri | كوفيٌّ عريض |
| `F-Kufam.dc.html` | Kufam | كوفيٌّ حديث |
| `F-Marhey.dc.html` | Marhey | حديثٌ مستدير |
| `F-Almarai.dc.html` | Almarai | هندسيٌّ نظيف |
| `F-Changa.dc.html` | Changa | هندسيٌّ مضغوط |
| `F-Cairo.dc.html` | Cairo | هندسيٌّ واسع |

السطرُ الذي فوق الاسمين (`حفل عقد قران`) والذي تحتهما (الأسماءُ
الكاملة) باقيان على خطَّي الدعوة — `Reem Kufi` و`Tajawal` — فيُحكم على
الاسمين في سياقهما لا مفردَين.

والمقاسُ مضبوطٌ لكلّ خطٍّ على حدة (٥٤–٧٠px) لأنّ ارتفاع الحرف يختلف
بين الخطوط: المقارنةُ بصريّةٌ لا رقميّة.

## إعادةُ البناء

```
node "<مجلّد مهارة design>/seed-canvas.mjs" \
  --template "<مجلّد مهارة design>/payload.template.html" \
  --out khutut-al-asma.html --title "خطوط أسماء العروسين" \
  --artboard Main.dc.html --artboard F-Aref.dc.html \
  --artboard F-Messiri.dc.html --artboard F-Amiri.dc.html \
  --artboard F-Qahiri.dc.html --artboard F-Kufam.dc.html \
  --artboard F-Marhey.dc.html --artboard F-Almarai.dc.html \
  --artboard F-Changa.dc.html --artboard F-Cairo.dc.html \
  --canvas canvas.json
```
