// مقارنة الداخل بالبكسل بين نسختين (قاعدة CLAUDE.md قبل كل تسليم).
// الاستخدام: OLD_URL=http://127.0.0.1:8770/approved.html NEW_URL=http://127.0.0.1:8770/index.html OUT=diff-out node innerdiff.js
// ثم: python3 innerdiff_compare.py diff-out
// يُسكت العشوائي: الوقت مثبّت (العدّاد)، Math.random ثابت، كل الحركات متوقفة.
const { chromium } = require('playwright'); const fs=require('fs');
const OLD=process.env.OLD_URL, NEW=process.env.NEW_URL, OUT=process.env.OUT||'diff-out';
if(!OLD||!NEW){ console.error('set OLD_URL and NEW_URL'); process.exit(1); }
fs.mkdirSync(OUT,{recursive:true});
(async () => {
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM||'/opt/pw-browsers/chromium', args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
  const shoot = async (url,tag,w,h,m) => {
    const p = await b.newPage({ viewport:{width:w,height:h}, deviceScaleFactor:1, isMobile:m, hasTouch:m });
    await p.addInitScript(()=>{ const T=new Date('2026-11-01T12:00:00+03:00').getTime(); const D=Date; class FD extends D{ constructor(...a){ super(...(a.length?a:[T])); } static now(){ return T; } } window.Date=FD; Math.random=()=>.5; });
    await p.goto(url); await p.waitForTimeout(2500);
    // وضع «الدعوة بلا حركة» يعرض الداخل مباشرة؛ نخفي طبقات الغلاف القديمة إن وجدت
    await p.evaluate(()=>{ document.getElementById('plainBtn').click(); ['doors','introZoom'].forEach(i=>{ const e=document.getElementById(i); if(e) e.style.display='none'; }); document.body.classList.add('doorsOpen'); const st=document.createElement('style'); st.textContent='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}'; document.head.appendChild(st); });
    await p.waitForTimeout(800);
    const n = await p.evaluate(()=>document.querySelectorAll('.scr').length);
    for(let i=0;i<n;i++){ await p.evaluate(i=>{ const s=document.querySelectorAll('.scr')[i]; s.scrollIntoView({block:'start'}); s.classList.add('on'); },i); await p.waitForTimeout(700); await p.screenshot({path:`${OUT}/${tag}_${i}.png`}); }
    await p.close(); return n;
  };
  for (const [w,h,m,v] of [[390,844,true,'m'],[375,667,true,'se'],[1280,800,false,'d']]) {
    const a=await shoot(OLD,'old_'+v,w,h,m), c=await shoot(NEW,'new_'+v,w,h,m); console.log(v,'screens',a,c);
  }
  await b.close();
})();
