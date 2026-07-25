// Content for every printable in the toolkit. Rendered to PDF by build.js.

const f = (label, kind = 'line') => `
  <div class="field"><label>${label}</label><div class="${kind}"></div></div>`;

const rows = (n, cols) =>
  Array.from({ length: n }, () => `<tr>${cols.map(c => `<td class="${c}"></td>`).join('')}</tr>`).join('');

const checks = items => `<ul class="checks">${items
  .map(i => (i.startsWith('#') ? `<li class="head">${i.slice(1)}</li>` : `<li>${i}</li>`))
  .join('')}</ul>`;

const clauses = items => `<ol class="clauses">${items
  .map(([t, b]) => `<li><b>${t}</b>${b}</li>`).join('')}</ol>`;

module.exports = [
  {
    slug: 'start-here',
    title: 'Start Here',
    lede: 'Seven minutes of setup, then this toolkit runs your admin for you. Work through it in order — each document feeds the next one.',
    body: `
      <h2>The order that works</h2>
      ${clauses([
        ['1 &middot; Set your price first', 'Open the <b>Pricing Calculator</b> and fill in your real hours and costs. Every other document depends on knowing your number. Do not skip this one.'],
        ['2 &middot; Put the intake form somewhere public', 'Link the <b>Client Intake Form</b> in your bio, your email signature, and your website. It answers budget, timeline and scope before you ever get on a call.'],
        ['3 &middot; Send the proposal within 24 hours', 'Momentum closes deals. Use the <b>Client Proposal</b> while the conversation is still warm, with three tiers so the question becomes <i>which one</i> rather than <i>whether</i>.'],
        ['4 &middot; Contract and deposit together', 'Send the <b>Service Contract</b> and the deposit invoice in the same email. Work starts when both come back — never before.'],
        ['5 &middot; Run the onboarding checklist', 'The <b>Client Onboarding Checklist</b> is what makes a one-person business feel established. Tick every box, every client.'],
        ['6 &middot; Invoice the same day you deliver', 'Use the <b>Invoice Template</b>. Late invoices become late payments.'],
        ['7 &middot; Log it', 'Add the payment to the <b>Income &amp; Expense Tracker</b> the day it lands, and plan next month in the <b>Content Planner</b>.'],
      ])}

      <h2>What is inside</h2>
      <table>
        <tr><th>File</th><th>Format</th><th>Use it when</th></tr>
        <tr><td>Pricing Calculator</td><td>Spreadsheet</td><td>Setting or raising your rates</td></tr>
        <tr><td>Client Intake Form</td><td>PDF</td><td>Before a discovery call</td></tr>
        <tr><td>Client Proposal</td><td>PDF</td><td>After the call, within 24 hours</td></tr>
        <tr><td>Service Contract</td><td>PDF</td><td>Before any work begins</td></tr>
        <tr><td>Onboarding Checklist</td><td>PDF</td><td>The first week of every project</td></tr>
        <tr><td>Invoice Template</td><td>PDF</td><td>Deposit, and again on delivery</td></tr>
        <tr><td>Income &amp; Expense Tracker</td><td>Spreadsheet</td><td>Every payment, every month</td></tr>
        <tr><td>Content Planner</td><td>PDF</td><td>Once a month, in one sitting</td></tr>
      </table>

      <div class="panel avoid-break">
        <h3>Make it yours</h3>
        <p class="note">Every PDF is supplied in A4 and US Letter. Replace the placeholder business name in the header, keep the structure, and change the wording wherever it does not sound like you — a document your client can tell you wrote is worth more than a perfect one you copied.</p>
      </div>

      <div class="panel avoid-break">
        <h3>One honest note about the contract</h3>
        <p class="note">The Service Contract is a plain-language starting point drafted for common freelance and small-service work. It is not legal advice and it is not tailored to your country or your situation. For high-value work, or anywhere the stakes are serious, have a qualified lawyer in your jurisdiction review it before you use it.</p>
      </div>`,
  },

  {
    slug: 'invoice',
    title: 'Invoice',
    lede: '',
    body: `
      <div class="grid">
        <div>
          <h2>From</h2>
          ${f('Business name')}${f('Contact name')}${f('Email')}${f('Phone')}
        </div>
        <div>
          <h2>Bill to</h2>
          ${f('Client / company')}${f('Contact name')}${f('Email')}${f('Address')}
        </div>
      </div>

      <div class="grid three">
        ${f('Invoice number')}${f('Issue date')}${f('Due date')}
      </div>

      <h2>Services</h2>
      <table>
        <tr><th style="width:52%">Description</th><th class="r">Qty</th><th class="r">Rate</th><th class="r">Amount</th></tr>
        ${rows(7, ['', 'r', 'r', 'r'])}
        <tr class="sum"><td class="lbl" colspan="3">Subtotal</td><td class="r"></td></tr>
        <tr class="sum"><td class="lbl" colspan="3">Tax / VAT</td><td class="r"></td></tr>
        <tr class="sum"><td class="lbl" colspan="3">Deposit already paid</td><td class="r"></td></tr>
        <tr class="total"><td class="lbl" colspan="3">Total due</td><td class="r"></td></tr>
      </table>

      <div class="grid" style="margin-top:20px">
        <div>
          <h2>Payment details</h2>
          ${f('Bank / account name')}${f('Account number / IBAN')}${f('Reference')}
        </div>
        <div>
          <h2>Terms</h2>
          <p class="note">Payment is due within <b>7 days</b> of the invoice date unless agreed otherwise in writing.</p>
          <p class="note">Invoices unpaid after the due date may carry a late fee of <b>5%</b> of the outstanding balance per week, and work on any active project may be paused until the balance is cleared.</p>
          <p class="note">Please quote the invoice number with your transfer so it can be matched to your account.</p>
        </div>
      </div>

      <div class="panel avoid-break" style="margin-top:22px">
        <p class="note"><b>Thank you.</b> If anything on this invoice looks wrong, reply to the email it came with and it will be corrected the same day.</p>
      </div>`,
  },

  {
    slug: 'proposal',
    title: 'Project Proposal',
    lede: 'Prepared for a specific client, on a specific date. Replace every bracket before sending — a proposal that still says [Client Name] loses the job.',
    body: `
      <div class="grid three">
        ${f('Prepared for')}${f('Prepared by')}${f('Date')}
      </div>

      <h2>1. What you told me</h2>
      <p class="note">Restate the problem in the client's own words. If they read this paragraph and think <i>yes, exactly</i>, the rest of the proposal barely has to work.</p>
      ${f('The problem, in their words', 'box tall')}

      <h2>2. What success looks like</h2>
      <p class="note">Describe the outcome, not the task list. Not "eight social posts" — "a month of content you do not have to think about."</p>
      ${f('The outcome', 'box')}

      <h2>3. Scope</h2>
      <div class="grid">
        <div>
          <h3>Included</h3>
          ${f('', 'box tall')}
        </div>
        <div>
          <h3>Not included</h3>
          ${f('', 'box tall')}
        </div>
      </div>
      <p class="note">The right-hand column is the one that protects you. Be specific about it.</p>

      <div class="page-break"></div>

      <h2>4. Investment</h2>
      <p class="note">Three tiers. Most clients choose the middle one — build it to be the option you actually want to sell.</p>
      <table>
        <tr><th style="width:20%">Tier</th><th style="width:52%">What it covers</th><th class="r">Price</th></tr>
        <tr><td><b>Essential</b></td><td></td><td class="r"></td></tr>
        <tr><td><b>Recommended</b></td><td></td><td class="r"></td></tr>
        <tr><td><b>Complete</b></td><td></td><td class="r"></td></tr>
      </table>

      <h2>5. Timeline</h2>
      <table>
        <tr><th style="width:24%">Stage</th><th style="width:52%">What happens</th><th class="r">By</th></tr>
        ${['Kick-off', 'First draft', 'Your feedback', 'Revisions', 'Delivery']
          .map(s => `<tr><td><b>${s}</b></td><td></td><td class="r"></td></tr>`).join('')}
      </table>
      <p class="note">Dates assume feedback comes back within the agreed window. Late feedback moves the delivery date by the same number of days.</p>

      <h2>6. How to say yes</h2>
      ${clauses([
        ['Reply with the tier you want', 'A single line is enough.'],
        ['Sign the contract', 'It will be in your inbox the same day.'],
        ['Pay the deposit', 'Work begins the moment it clears, on the start date above.'],
      ])}

      <div class="panel avoid-break">
        <p class="note">This proposal is valid for <b>14 days</b> from the date above. After that, pricing and availability may change.</p>
      </div>`,
  },

  {
    slug: 'contract',
    title: 'Service Agreement',
    lede: 'A plain-language agreement for freelance and small-service work. Fill in the brackets, delete what does not apply, and keep a signed copy.',
    body: `
      <div class="grid">
        <div>
          <h2>The provider</h2>
          ${f('Name / business')}${f('Address')}${f('Email')}
        </div>
        <div>
          <h2>The client</h2>
          ${f('Name / company')}${f('Address')}${f('Email')}
        </div>
      </div>
      <div class="grid three">${f('Project')}${f('Start date')}${f('Agreement date')}</div>

      <h2>Terms</h2>
      ${clauses([
        ['Scope of work', 'The provider will deliver the work described in the attached proposal dated [____], which forms part of this agreement. Anything not written in that proposal is outside the scope of this agreement.'],
        ['Fees', 'The total fee for the work is [____]. Prices are exclusive of tax unless stated otherwise.'],
        ['Payment schedule', 'A non-refundable deposit of <b>50%</b> is payable before work begins. The balance is due on delivery, within <b>7 days</b> of the final invoice date. The provider is not obliged to begin or continue work while any payment is outstanding.'],
        ['Late payment', 'Balances unpaid after the due date may carry a late fee of <b>5%</b> per week. Work may be paused, and delivered files withheld, until the account is settled.'],
        ['Revisions', 'The fee includes <b>two</b> rounds of revisions. A round means one consolidated set of feedback. Further rounds, or changes requested after final approval, are billed at [____] per hour.'],
        ['Changes to scope', 'Either party may propose a change to the scope. Changes only take effect once both parties agree the revised work, price and timeline in writing.'],
        ['Client responsibilities', 'The client will supply all content, access, approvals and materials the work depends on, and will respond to requests for feedback within <b>5 working days</b>. The provider is not responsible for delays caused by late materials or feedback.'],
        ['Inactivity', 'If the client is unreachable for <b>30 consecutive days</b>, the project may be treated as paused. Restarting it may require a rescheduling fee and a new timeline based on the provider&rsquo;s availability at that time.'],
        ['Ownership', 'On receipt of final payment in full, ownership of the final delivered work transfers to the client. Until then, all rights remain with the provider. Working files, source materials and unused concepts remain the property of the provider unless separately agreed in writing.'],
        ['Third-party materials', 'Fonts, stock imagery, plugins and similar licensed assets are licensed to the client at the client&rsquo;s cost, under those third parties&rsquo; terms. Ongoing licence renewals are the client&rsquo;s responsibility.'],
        ['Portfolio rights', 'The provider may show the completed work in a portfolio, on social media and in marketing materials, unless the client asks in writing for it to be kept private.'],
        ['Confidentiality', 'Each party will keep the other&rsquo;s non-public business information confidential, and will not share it with anyone except where the law requires it.'],
        ['Cancellation', 'Either party may end this agreement in writing. If the client cancels, the deposit is not refunded and any work completed beyond the deposit is invoiced at the agreed rate. If the provider cancels, any fees paid for work not yet delivered are refunded.'],
        ['Independent contractor', 'The provider is an independent contractor, not an employee, and is responsible for their own taxes, insurance and equipment.'],
        ['Limitation of liability', 'Neither party is liable for indirect or consequential losses. The provider&rsquo;s total liability under this agreement is limited to the total fees actually paid by the client.'],
        ['Governing law', 'This agreement is governed by the laws of [____], and both parties agree to that jurisdiction.'],
        ['Whole agreement', 'This document and the attached proposal are the entire agreement between the parties and replace any earlier discussions. Changes must be in writing and signed by both.'],
      ])}

      <div class="sign avoid-break">
        <div>
          <h2>Provider</h2>
          ${f('Signature')}${f('Name')}${f('Date')}
        </div>
        <div>
          <h2>Client</h2>
          ${f('Signature')}${f('Name')}${f('Date')}
        </div>
      </div>

      <div class="panel avoid-break">
        <p class="note"><b>Not legal advice.</b> This template is a plain-language starting point, not a document tailored to your country, your industry or your situation. For high-value or high-risk work, have a qualified lawyer in your jurisdiction review it before you rely on it.</p>
      </div>`,
  },

  {
    slug: 'client-intake-form',
    title: 'Client Intake Form',
    lede: 'Send this before the first call. It qualifies the enquiry, kills the back-and-forth, and lets you quote with confidence.',
    body: `
      <h2>About you</h2>
      <div class="grid">${f('Name')}${f('Business name')}${f('Email')}${f('Phone / preferred contact')}</div>
      ${f('Website and social links')}

      <h2>The project</h2>
      ${f('What do you need help with?', 'box')}
      ${f('What have you already tried?', 'box')}
      ${f('What does a great result look like to you?', 'box')}

      <h2>Practicalities</h2>
      <div class="grid">
        ${f('Ideal start date')}
        ${f('Hard deadline, if any')}
        ${f('Budget range')}
        ${f('Who signs off on this?')}
      </div>
      <p class="note">Budget is asked up front on purpose. It is the fastest way to find out whether this is a good fit for both of us — and it saves you a call if it is not.</p>

      <div class="page-break"></div>

      <h2>Working together</h2>
      ${f('Is there a style, tone or example you love?', 'box')}
      ${f('Anything you definitely do not want?', 'box')}
      ${f('Who else is involved in decisions?')}
      ${f('How did you hear about me?')}

      <h2>Anything else</h2>
      ${f('', 'box tall')}

      <div class="panel avoid-break">
        <p class="note"><b>What happens next.</b> Your answers will be reviewed within one working day. If it looks like a fit, you will get a link to book a call. If it is not the right fit, you will get an honest reply saying so — and, where possible, a recommendation for someone who is.</p>
      </div>`,
  },

  {
    slug: 'onboarding-checklist',
    title: 'Client Onboarding Checklist',
    lede: 'Run this for every client, without exception. Consistency is the whole point — it is what makes a one-person business feel established.',
    body: `
      <div class="grid">
        <div>
          <h2>Before you say yes</h2>
          ${checks([
            'Intake form received and read in full',
            'Budget confirmed as workable',
            'Timeline checked against your current load',
            'Decision-maker identified by name',
            'Discovery call held and notes written up',
            'Any red flags noted and honestly weighed',
          ])}

          <h2>Winning the work</h2>
          ${checks([
            'Proposal sent within 24 hours of the call',
            'Three tiers offered, middle one recommended',
            'Scope exclusions written down explicitly',
            'Follow-up sent if no reply after 3 days',
            'Tier confirmed in writing',
          ])}

          <h2>Locking it in</h2>
          ${checks([
            'Contract sent with the deposit invoice',
            'Signed contract received and filed',
            'Deposit cleared in your account',
            'Start date confirmed to the client',
            'Project added to your calendar and tracker',
          ])}
        </div>
        <div>
          <h2>First week</h2>
          ${checks([
            'Welcome email sent with next steps',
            'All materials and access received',
            'Shared folder or workspace set up',
            'Timeline sent with feedback windows marked',
            'Communication channel and hours agreed',
            'Revision policy restated in plain language',
          ])}

          <h2>During the project</h2>
          ${checks([
            'Halfway check-in sent unprompted',
            'Feedback consolidated into one round',
            'Out-of-scope requests logged, quoted, not absorbed',
            'Delivery date reconfirmed a week out',
          ])}

          <h2>Delivery and after</h2>
          ${checks([
            'Final files delivered in agreed formats',
            'Final invoice sent the same day',
            'Payment received and logged in the tracker',
            'Testimonial requested while they are happy',
            'Portfolio permission confirmed',
            'Calendar reminder set to check in at 60 days',
          ])}
        </div>
      </div>

      <div class="panel avoid-break">
        <h3>The two boxes people skip</h3>
        <p class="note"><b>The halfway check-in</b> costs you one message and prevents almost every unpleasant surprise at delivery. <b>The testimonial request</b> has a short window — ask on the day they are delighted, not three months later.</p>
      </div>`,
  },

  {
    slug: 'content-planner',
    title: 'Monthly Content Planner',
    lede: 'Fill this in once a month, in one sitting. Batching is what makes showing up consistently survivable.',
    body: `
      <div class="grid three">${f('Month')}${f('Main business goal')}${f('Posting days')}</div>

      <h2>Your four pillars</h2>
      <p class="note">Decide these once and reuse them for a year. Every post belongs to one of them — if it fits none, it does not get posted.</p>
      <div class="grid">
        ${f('1 — Teach (what you know)')}
        ${f('2 — Show (work and process)')}
        ${f('3 — Prove (results, clients, before/after)')}
        ${f('4 — Connect (you, opinions, story)')}
      </div>

      <h2>The month</h2>
      <table>
        <tr><th style="width:9%">Date</th><th style="width:15%">Pillar</th><th style="width:44%">Idea / hook</th><th style="width:16%">Format</th><th>Done</th></tr>
        ${rows(14, ['', '', '', '', ''])}
      </table>

      <div class="page-break"></div>

      <table>
        <tr><th style="width:9%">Date</th><th style="width:15%">Pillar</th><th style="width:44%">Idea / hook</th><th style="width:16%">Format</th><th>Done</th></tr>
        ${rows(14, ['', '', '', '', ''])}
      </table>

      <h2>What actually worked</h2>
      <table>
        <tr><th style="width:52%">Top performing post</th><th class="r">Reach</th><th class="r">Saves</th><th class="r">Enquiries</th></tr>
        ${rows(5, ['', 'r', 'r', 'r'])}
      </table>

      <div class="panel avoid-break">
        <h3>Next month, do more of</h3>
        ${f('', 'box')}
        <p class="note">Judge posts by saves and enquiries, not likes. Likes tell you a post was pleasant. Saves tell you it was useful, and useful is what brings people back to buy.</p>
      </div>`,
  },
];
