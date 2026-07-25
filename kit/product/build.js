const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const docs = require('./docs');

const HERE = __dirname;
const OUT = path.join(HERE, 'out');
const BRAND = process.env.KIT_BRAND || 'HERERA';

const PAGES = [
  { name: 'A4', format: 'A4' },
  { name: 'US-Letter', format: 'Letter' },
];

const page_html = doc => `<!doctype html>
<meta charset="utf-8">
<title>${doc.title}</title>
<link rel="stylesheet" href="./doc.css">
<body>
  <header class="doc">
    <div class="doc-title">${doc.title}</div>
    <div class="doc-brand">${BRAND}<br>Small Business Toolkit</div>
  </header>
  ${doc.lede ? `<p class="lede">${doc.lede}</p>` : ''}
  ${doc.body}
</body>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  for (const size of PAGES) {
    const dir = path.join(OUT, size.name);
    fs.mkdirSync(dir, { recursive: true });

    for (const doc of docs) {
      // Chromium blocks file:// subresources from an about:blank document, so the
      // page has to be served from a real file next to doc.css for styles to apply.
      const tmp = path.join(HERE, `.build-${doc.slug}.html`);
      fs.writeFileSync(tmp, page_html(doc));
      await page.goto('file://' + tmp, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.pdf({
        path: path.join(dir, `${doc.slug}.pdf`),
        format: size.format,
        printBackground: true,
        margin: { top: '16mm', bottom: '16mm', left: '16mm', right: '16mm' },
        displayHeaderFooter: true,
        headerTemplate: '<div></div>',
        footerTemplate:
          `<div style="width:100%;font-size:7pt;color:#8A8172;font-family:Helvetica,sans-serif;` +
          `padding:0 16mm;display:flex;justify-content:space-between">` +
          `<span>${BRAND} &middot; Small Business Toolkit</span>` +
          `<span class="pageNumber"></span></div>`,
      });
      fs.unlinkSync(tmp);
      process.stdout.write(`  ✓ ${size.name}/${doc.slug}.pdf\n`);
    }
  }

  await browser.close();
  console.log(`\n${docs.length * PAGES.length} PDFs written to kit/product/out/`);
})();
