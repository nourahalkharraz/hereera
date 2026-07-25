# Small Business Toolkit — product + traffic engine

Everything needed to sell a digital product on Gumroad using Pinterest as the
traffic source. The product, the pins, and the copy are all generated from source
files in this folder, so any of it can be regenerated after an edit.

```
kit/
├── product/          the thing that gets sold
│   ├── docs.js         content of the 7 printables  ← edit wording here
│   ├── doc.css         how the printables look
│   ├── build.js        docs.js → PDFs (A4 + US Letter)
│   ├── sheets.py       the 2 spreadsheets, with live formulas
│   └── out/            ← the files you upload to Gumroad
├── pins/             the traffic engine
│   ├── pins.json       pin copy + Pinterest SEO  ← edit headlines here
│   ├── pin.html        6 pin layouts, 6 colourways
│   ├── render.js       pins.json → 1000×1500 PNGs
│   └── out/            ← the images you upload to Pinterest
│       └── manifest.json   title + description + board for every image
├── copy/
│   ├── gumroad-listing.md  paste straight into Gumroad
│   └── pinterest-plan.md   setup, boards, 30-day schedule
└── assets/fonts/     Playfair Display, Inter, DM Sans (bundled, no network needed)
```

## Rebuilding

```bash
export NODE_PATH=/opt/node22/lib/node_modules

cd kit/product && node build.js && python3 sheets.py   # 14 PDFs + 2 spreadsheets
cd ../pins     && node render.js --variants=3          # 54 pins + manifest
```

Set a different business name on the documents with `KIT_BRAND="Your Name"` before
either command. Change the brand on the pins in `pins.json` (`brand`), and set
`productUrl` there to the real Gumroad link before rendering — it is written into
`manifest.json` for every pin.

## Order of operations

1. `kit/product/out/` → upload to Gumroad, using `kit/copy/gumroad-listing.md`
2. Copy the live Gumroad URL into `pins.json` → `productUrl`
3. Re-run `render.js` so every pin carries the real link
4. `kit/pins/out/` → upload to Pinterest, following `kit/copy/pinterest-plan.md`

## Editing

- **Change the wording of a document** → `product/docs.js`, then `node build.js`
- **Change how documents look** → `product/doc.css`
- **Add or reword a pin** → `pins.json`, then `node render.js`
- **Add a pin layout or colourway** → `pin.html` (`T` object, `PALETTES` object)
