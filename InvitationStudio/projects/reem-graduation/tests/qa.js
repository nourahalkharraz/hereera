const { chromium } = require('playwright');
const fs=require('fs');
const BASE=process.env.QA_BASE||'http://127.0.0.1:8770/index.html'; const OUT=process.env.QA_OUT||'qa-out'; fs.mkdirSync(OUT,{recursive:true});
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
  const R={};
  const vps=[['m',390,844,true],['se',375,667,true],['pm',430,932,true],['d',1280,800,false]];
  for (const [tag,w,h,mob] of vps) {
    const ctx = await b.newContext({ viewport:{width:w,height:h}, deviceScaleFactor:2, isMobile:mob, hasTouch:mob, permissions:['clipboard-read','clipboard-write'], acceptDownloads:true });
    const p = await ctx.newPage(); const r={errs:[],bad:[],failed:[]};
    p.on('pageerror',e=>r.errs.push('pageerror: '+e.message)); p.on('console',m=>{ if(m.type()==='error') r.errs.push(m.text().slice(0,160)); });
    p.on('response',x=>{ if(x.status()>=400) r.bad.push(x.status()+' '+x.url()); }); p.on('requestfailed',x=>r.failed.push(x.url().slice(0,120)+' '+(x.failure()||{}).errorText));
    const t0=Date.now(); await p.goto(BASE);
    await p.waitForFunction(()=>document.body.classList.contains('ready'),null,{timeout:40000}); r.readyS=((Date.now()-t0)/1000).toFixed(1);
    await p.waitForTimeout(2500); await p.screenshot({path:`${OUT}/qa_${tag}_cover.png`});
    r.cover=await p.evaluate(()=>({title:document.querySelector('.title h1').textContent.trim(),sub:document.querySelector('.title i').textContent.trim(),small:document.querySelector('.title small').textContent.trim(),cta:document.getElementById('openBtn').textContent.trim(),hx:document.documentElement.scrollWidth>document.documentElement.clientWidth}));
    await p.click('#openBtn'); await p.waitForFunction(()=>window.__phaseGet&&window.__phaseGet()==='reveal',null,{timeout:20000}); await p.waitForTimeout(2500);
    const sc=await p.evaluate(()=>document.querySelectorAll('.scr').length); r.screens=sc; r.overflow=[];
    for(let i=0;i<sc;i++){ await p.evaluate(i=>document.querySelectorAll('.scr')[i].scrollIntoView({block:'start'}),i); await p.waitForTimeout(1100); if(tag!=='pm') await p.screenshot({path:`${OUT}/qa_${tag}_s${i}.png`});
      const o=await p.evaluate(()=>{ const pg=document.querySelector('.pg').getBoundingClientRect(); const out=[]; document.querySelectorAll('.pg *').forEach(el=>{ const q=el.getBoundingClientRect(); if(!q.width||q.bottom<0||q.top>innerHeight) return; if(q.right>pg.right+2||q.left<pg.left-2){ const cs=getComputedStyle(el); if(cs.visibility!=='hidden'&&cs.display!=='none'&&!el.closest('.p-side,.p-spray')) out.push((el.id||el.className||el.tagName).toString().slice(0,30)+':'+Math.round(q.left)+'-'+Math.round(q.right)); } }); return out.slice(0,6); });
      if(o.length) r.overflow.push('s'+i+' '+o.join(' ')); }
    if(tag==='m'){
      // text audit
      r.text=await p.evaluate(()=>document.querySelector('.pg').innerText.replace(/\n+/g,' | ').slice(0,3000));
      // RSVP empty
      await p.evaluate(()=>document.querySelector('#rsvp').scrollIntoView());
      await p.click('#rsvp button[data-v=yes]'); await p.waitForTimeout(300);
      r.rsvpEmpty=await p.evaluate(()=>({valid:document.getElementById('rsvp').checkValidity(),toast:document.getElementById('rsvpToast').textContent}));
      await p.fill('#rsvpName','فاطمة'); await p.click('.r-cnt .cp'); await p.click('.r-cnt .cp'); 
      await p.click('#rsvp button[data-v=yes]'); await p.waitForTimeout(800);
      r.rsvpYes=await p.evaluate(async()=>({toast:document.getElementById('rsvpToast').textContent,count:document.getElementById('rsvp').dataset.count,clip:await navigator.clipboard.readText().catch(e=>'ERR '+e.message)}));
      await p.click('#rsvp button[data-v=no]'); await p.waitForTimeout(800);
      r.rsvpNo=await p.evaluate(async()=>({toast:document.getElementById('rsvpToast').textContent,clip:await navigator.clipboard.readText().catch(e=>'ERR '+e.message)}));
      await p.screenshot({path:OUT+'/qa_m_rsvp.png'});
      // buttons
      await p.evaluate(()=>document.getElementById('copyAddr').scrollIntoView()); await p.click('#copyAddr'); await p.waitForTimeout(400);
      r.copyAddr=await p.evaluate(async()=>({toast:document.getElementById('addrToast').textContent,clip:await navigator.clipboard.readText().catch(e=>'ERR')}));
      await p.evaluate(()=>document.getElementById('shareBtn').scrollIntoView()); await p.click('#shareBtn'); await p.waitForTimeout(500);
      r.share=await p.evaluate(async()=>({hasShare:!!navigator.share,toast:document.getElementById('shareToast').textContent,clip:await navigator.clipboard.readText().catch(e=>'ERR')}));
      r.links=await p.evaluate(()=>[...document.querySelectorAll('.pg a[href^=http]')].map(a=>a.textContent.trim()+' -> '+decodeURIComponent(a.href).slice(0,160)));
      r.icsHidden=await p.evaluate(()=>document.getElementById('icsBtn').hidden);
      const dl=p.waitForEvent('download',{timeout:15000}).then(d=>d.suggestedFilename()).catch(e=>'NO DOWNLOAD: '+e.message.slice(0,60));
      await p.evaluate(()=>document.getElementById('saveImg').scrollIntoView()); await p.click('#saveImg'); r.saveImg=await dl;
      // روابط قائمة الأقسام: تُفحص بلمس حقيقي في qanav.js (النقر البرمجي هنا كان يعطي نتيجة خاطئة)
      // EN toggle
      await p.evaluate(()=>{ const a=document.querySelector('.p-nav a.lang'); a.click(); }); await p.waitForTimeout(600);
      r.en=await p.evaluate(()=>({en:document.querySelector('.pg').classList.contains('en'),name:document.querySelector('.p-name').textContent,kick:document.querySelector('.p-kick2').textContent,dir:document.querySelector('.pg').dir||getComputedStyle(document.querySelector('.pg')).direction,lang:document.querySelector('.p-nav a.lang').textContent}));
      await p.evaluate(()=>document.querySelectorAll('.scr')[0].scrollIntoView()); await p.waitForTimeout(900); await p.screenshot({path:OUT+'/qa_m_en0.png'});
      await p.evaluate(()=>document.querySelectorAll('.scr')[3].scrollIntoView()); await p.waitForTimeout(900); await p.screenshot({path:OUT+'/qa_m_en3.png'});
      await p.evaluate(()=>document.querySelector('.p-nav a.lang').click()); await p.waitForTimeout(400);
      r.enBack=await p.evaluate(()=>({en:document.querySelector('.pg').classList.contains('en'),name:document.querySelector('.p-name').textContent}));
    }
    R[tag]=r; await ctx.close();
  }
  // reduced motion
  { const ctx=await b.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true,reducedMotion:'reduce'}); const p=await ctx.newPage(); const r={errs:[]}; p.on('pageerror',e=>r.errs.push(e.message));
    const t0=Date.now(); await p.goto(BASE); await p.waitForFunction(()=>document.body.classList.contains('ready'),null,{timeout:30000}); r.readyS=((Date.now()-t0)/1000).toFixed(1); await p.waitForTimeout(800); await p.screenshot({path:OUT+'/qa_rm_cover.png'});
    await p.click('#openBtn'); await p.waitForFunction(()=>window.__phaseGet()==='reveal',null,{timeout:15000}).then(()=>r.reveal=true).catch(()=>r.reveal=false); R.reduced=r; await ctx.close(); }
  fs.writeFileSync(OUT+'/qa.json',JSON.stringify(R,null,1)); await b.close(); console.log('done');
})();
