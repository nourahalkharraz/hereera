# Pinterest plan — the traffic engine

Pinterest is a search engine, not a social network. Nobody has to follow you. A pin
that matches a search keeps sending traffic for months. That is why this is the
channel, and why the work is front-loaded rather than daily.

**Expected timeline:** first traffic in 3–6 weeks, meaningful traffic in 8–12 weeks.
Anyone promising faster is selling something.

---

## Step 1 — Account setup (30 minutes, once)

1. Convert to a **Pinterest Business account** (free) — you need Analytics.
2. **Claim your Gumroad domain** under Settings → Claimed accounts. Claimed links
   rank better and get attribution.
3. **Profile name:** `Your Name | Small Business Templates & Tools`
   The words after the pipe are searchable. Do not waste them on an aesthetic.
4. **Bio:** `Templates and systems for people running a business on their own.
   Invoices, contracts, pricing, and the paperwork nobody teaches you.`
5. Turn on **Rich Pins** — free, and it pulls your product title and price onto the pin.

---

## Step 2 — Boards (20 minutes, once)

Create these five. Board names and descriptions are ranked content, so write them
with keywords, not personality.

| Board | Description to paste |
|---|---|
| **Small Business Templates** | Editable invoice templates, contract templates, client proposals and business printables for freelancers and small business owners. |
| **Pricing & Money** | How to price your services, pricing calculators, freelance rates, small business bookkeeping and cash flow tips. |
| **Client Onboarding** | Client onboarding checklists, intake forms, welcome processes and contract tips for service businesses. |
| **Business Organization** | Small business organization, systems, planners and productivity for solopreneurs and freelancers. |
| **Starting a Small Business** | Checklists, first steps and beginner tips for starting a small business or side hustle. |

Each pin in `out/manifest.json` already names the board it belongs to.

---

## Step 3 — Pinning rules

**Every pin needs three things:**

1. **Title** — keyword first, benefit second. Max ~40 characters visible.
2. **Description** — 2–3 sentences, natural language, keywords woven in.
   Pinterest reads this. Keyword-stuffing gets suppressed; writing normally wins.
3. **Link** — your Gumroad product URL. Every single pin.

All three are pre-written for you in `kit/pins/out/manifest.json`, one entry per image.

**Rules that matter:**

- **5 pins a day, maximum.** More looks like spam to the algorithm.
- **Never post the same image twice.** Different image, same link is fine and
  encouraged — that is what the palette variants are for.
- **Space repeats of the same link by 7+ days.**
- **Do not delete underperforming pins.** They take weeks to find their audience.
- Post in **your own morning** — Pinterest weights early engagement, and your
  audience is mostly asleep in the US when it is evening in the Gulf. Anywhere
  between 8am and 11am your time is fine.

---

## Step 4 — The 30-day schedule

You have 18 base pins. Run `node render.js --variants=3` in `kit/pins/` to turn
those into 54 images — same headlines, different colourways — which is enough for
30 days at 2 a day with room to spare.

| Days | What to post | Per day |
|---|---|---|
| 1–3 | The hero pins: `01`, `15`, `18` — these describe the product | 1 |
| 4–14 | The value pins: `02`–`14`, one per day, rotating boards | 1 |
| 15–21 | Best 3 performers from days 1–14, in a different colourway | 2 |
| 22–30 | Remaining base pins + variants, 2 a day | 2 |

**At day 30, look at Analytics and answer one question:** which three pins got the
most *saves*? Saves predict traffic better than impressions. Whatever those three
have in common — the template, the topic, the colour — make ten more like them.
That is the entire optimisation loop.

---

## Step 5 — What to do with the data

Check Pinterest Analytics **weekly, not daily**. Pins take weeks to move; daily
checking will only make you anxious and tempted to delete things too early.

Track these three numbers in a note:

| Week | Impressions | Saves | Outbound clicks |
|---|---|---|---|

**Outbound clicks are the only number connected to money.** Impressions can be in
the thousands with zero clicks — that means the pin looks nice but does not promise
anything. Rewrite the headline to promise something specific.

---

## Realistic expectations

- Weeks 1–3: almost nothing. This is normal and is not a sign it failed.
- Weeks 4–8: impressions climb, first outbound clicks appear.
- Weeks 8–12: if the product and pins match, first sales.

**Rough arithmetic:** Pinterest → Gumroad converts at roughly 1–3%. At $14, one sale
per 50 clicks means you need around 1,500–3,000 monthly impressions before sales
become steady. That is achievable with consistent pinning. It is not achievable in
a week — and that is the honest version nobody puts in a screenshot.

---

## If you want to add TikTok later

Same content, different format. Every `list` pin is already a TikTok script — the
headline is the hook, the five items are the five beats. But do Pinterest first and
alone: two channels started at once usually means neither gets done properly.
