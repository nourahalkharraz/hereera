const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport:{width:390,height:844}, deviceScaleFactor:1, isMobile:true, hasTouch:true });
  await p.goto((process.env.QA_BASE||'http://127.0.0.1:8770/index.html')); await p.waitForFunction(()=>document.body.classList.contains('ready'),null,{timeout:40000});
  await p.click('#openBtn'); await p.waitForFunction(()=>window.__phaseGet()==='reveal'); await p.waitForTimeout(3000);
  const out=[];
  for(const k of [0,1,2,3]){
    await p.evaluate(()=>document.scrollingElement.scrollTo({top:innerHeight,behavior:'auto'})); await p.waitForTimeout(800);
    const info=await p.evaluate(k=>{ const a=document.querySelectorAll('.p-nav a')[k]; const r=a.getBoundingClientRect(); return {t:a.textContent.trim(),h:a.getAttribute('href'),x:r.left+r.width/2,y:r.top+r.height/2}; },k);
    await p.touchscreen.tap(info.x,info.y);
    let tops=[]; for(let i=0;i<8;i++){ await p.waitForTimeout(500); tops.push(await p.evaluate(h=>Math.round(document.querySelector(h).getBoundingClientRect().top),info.h)); }
    out.push(info.t+' '+info.h+' tops: '+tops.join(','));
  }
  console.log(out.join('\n')); await b.close();
})();
