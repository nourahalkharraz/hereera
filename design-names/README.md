# أسماء العروسين — لوحةُ اقتراحات

خمسةُ اقتراحاتٍ لكتلة الاسمين داخلَ الدعوة، وبجانبها المعتمدةُ للمقارنة.
لم يُطبَّق شيءٌ منها على `invitation/index.html` — تنتظر الاختيار.

| الملفّ | الاقتراح | المحور |
|---|---|---|
| `Main.dc.html` | المعتمدة الآن | مرجعٌ للمقارنة |
| `A-Sprig.dc.html` | أ · فاصلٌ نباتيّ | الفاصلُ وحدَه |
| `B-Stacked.dc.html` | ب · لقبٌ تحت كلّ اسم | ترتيبُ الألقاب |
| `C-Vertical.dc.html` | ج · متراكبان رأسيّاً | اتّجاهُ الكتلة |
| `D-Amiri.dc.html` | د · بخطّ الأميري | الخطّ |
| `E-Cartouche.dc.html` | هـ · إطارٌ محفور | حدٌّ حول الكتلة |

القيمُ كلُّها مأخوذةٌ من الدعوة لا مقدَّرة: خطُّ `Reem Kufi` وزن ٧٠٠
بمقاس ٥٨٫٥px (ما يعطيه `clamp(42px, 15vw, 84px)` عند عرض ٣٩٠)،
والتدرّج `#4D5033 ← #666848`، والأسماءُ الكاملة `#6E5E53`، والفاصل
`#818263`. وكلُّ بطاقةٍ تعرض السطرَ الذي فوق والذي تحت، فيُحكم على
الكتلة في سياقها لا على الاسمين وحدَهما.

## إعادةُ البناء

```
node "<مجلّد مهارة design>/seed-canvas.mjs" \
  --template "<مجلّد مهارة design>/payload.template.html" \
  --out asma-al-arousain.html --title "أسماء العروسين" \
  --artboard Main.dc.html --artboard A-Sprig.dc.html \
  --artboard B-Stacked.dc.html --artboard C-Vertical.dc.html \
  --artboard D-Amiri.dc.html --artboard E-Cartouche.dc.html \
  --canvas canvas.json
```
