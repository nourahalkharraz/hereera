const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const DATA = JSON.parse(fs.readFileSync(path.join(HERE, 'pins.json'), 'utf8'));
const OUT = path.join(HERE, 'out');

// Extra palettes used when fanning out variants of the same pin.
const FANOUT = ['cream', 'sage', 'navy', 'blush', 'ivory', 'charcoal'];

const args = process.argv.slice(2);
const variants = Math.max(1, parseInt((args.find(a => a.startsWith('--variants=')) || '').split('=')[1] || '1', 10));

(async () => {
  fs.mkdirSync(OUT, { recursive: true });

  const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined });
  const page = await browser.newPage({
    viewport: { width: 1000, height: 1500 },
    deviceScaleFactor: 2,
  });
  await page.goto('file://' + path.join(HERE, 'pin.html'));
  await page.waitForFunction(() => typeof window.renderPin === 'function');

  const manifest = [];

  for (const pin of DATA.pins) {
    // variant 0 keeps the authored palette; later variants rotate through FANOUT
    const palettes = [pin.palette];
    for (let i = 1; i < variants; i++) {
      const next = FANOUT[(FANOUT.indexOf(pin.palette) + i) % FANOUT.length];
      palettes.push(next);
    }

    for (let v = 0; v < palettes.length; v++) {
      const data = { ...pin, palette: palettes[v], brand: DATA.brand };
      await page.evaluate(d => window.renderPin(d), data);
      await page.evaluate(() => document.fonts.ready);

      const file = v === 0 ? `${pin.id}.png` : `${pin.id}--${palettes[v]}.png`;
      await page.screenshot({ path: path.join(OUT, file), type: 'png' });

      manifest.push({
        file,
        board: pin.board,
        title: pin.pinTitle,
        description: pin.pinDescription,
        keywords: pin.keywords,
        link: DATA.productUrl,
      });
      process.stdout.write(`  ✓ ${file}\n`);
    }
  }

  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log(`\n${manifest.length} pins rendered into kit/pins/out/`);
})();
