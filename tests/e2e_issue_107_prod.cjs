const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const BASE = process.env.QV_BASE_URL || "https://joyceradis.github.io/Quem-Votar/";
const results = [];
async function check(name, fn) { try { await fn(); results.push({name,ok:true}); } catch(e) { results.push({name,ok:false,error:String(e.stack||e)}); throw e; } }
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const ctx=await browser.newContext({viewport:{width:1366,height:900}});
  await ctx.addInitScript(()=>localStorage.removeItem("qv_compare"));
  const page=await ctx.newPage();
  await page.goto(BASE+"candidatos.html",{waitUntil:"networkidle"});
  await page.waitForSelector("button[data-compare-id]");
  const buttons=page.locator("button[data-compare-id]");
  assert.ok(await buttons.count()>=4);
  const ids=await buttons.evaluateAll(xs=>xs.slice(0,4).map(x=>x.dataset.compareId));
  await check("1 candidatura: CTA bloqueado + teclado + foco",async()=>{
   await buttons.nth(0).focus(); await page.keyboard.press("Enter");
   assert.equal(await buttons.nth(0).getAttribute("aria-pressed"),"true");
   assert.match(await page.locator("#compareCount").innerText(),/Escolha mais 1/);
   assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"),"true");
   assert.equal(await page.evaluate(()=>document.activeElement?.dataset?.compareId),ids[0]);
  });
  await check("2 candidaturas: comparação habilitada",async()=>{
   await page.locator('button[data-compare-id="'+ids[1]+'"]').focus(); await page.keyboard.press("Enter");
   assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"),"false");
   assert.match(await page.locator("#openCompare").getAttribute("href"),/comparar\.html\?ids=/);
  });
  await check("3 candidaturas: limite explícito",async()=>{
   await page.locator('button[data-compare-id="'+ids[2]+'"]').focus(); await page.keyboard.press("Enter");
   assert.match(await page.locator("#compareCount").innerText(),/Limite de 3/);
   assert.equal(await page.locator('button[data-compare-id="'+ids[3]+'"]').isDisabled(),true);
   assert.equal(await page.locator('button[data-compare-id="'+ids[3]+'"]').getAttribute("aria-disabled"),"true");
  });
  await check("remoção: reabilita seleção e preserva foco",async()=>{
   const b=page.locator('button[data-compare-id="'+ids[1]+'"]'); await b.focus(); await page.keyboard.press("Enter");
   assert.equal(await page.evaluate(()=>document.activeElement?.dataset?.compareId),ids[1]);
   assert.equal(await page.locator('button[data-compare-id="'+ids[3]+'"]').isDisabled(),false);
   assert.equal(await page.locator("#openCompare").getAttribute("aria-disabled"),"false");
  });
  await check("URL duplicada/inválida: normalização canônica",async()=>{
   await page.goto(BASE+"comparar.html?ids="+encodeURIComponent(ids[0]+","+ids[0]+",invalid,"+ids[2]),{waitUntil:"networkidle"});
   assert.equal(await page.locator(".compare-person").count(),2);
   const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem("qv_compare")||"[]"));
   assert.deepEqual(stored,[ids[0],ids[2]]);
  });
  await check("URL com 1 candidatura: não renderiza comparação",async()=>{
   await page.goto(BASE+"comparar.html?ids="+encodeURIComponent(ids[0]),{waitUntil:"networkidle"});
   assert.equal(await page.locator(".compare-person").count(),0);
   assert.match(await page.locator("#compareMount").innerText(),/Escolha mais 1 pessoa/);
  });
  await ctx.close();
  const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  await mobile.addInitScript(()=>localStorage.removeItem("qv_compare"));
  const m=await mobile.newPage();
  await check("mobile 390x844: sem overflow horizontal e controles utilizáveis",async()=>{
   await m.goto(BASE+"candidatos.html",{waitUntil:"networkidle"});
   await m.waitForSelector("button[data-compare-id]");
   const overflow=await m.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
   assert.ok(overflow<=1,"horizontal overflow="+overflow);
   const first=m.locator("button[data-compare-id]").first(); await first.scrollIntoViewIfNeeded(); assert.equal(await first.isVisible(),true);
   await first.tap(); assert.equal(await first.getAttribute("aria-pressed"),"true");
   assert.equal(await m.locator("#compareTray").isVisible(),true);
  });
  await mobile.close();
  console.log(JSON.stringify({base:BASE,results},null,2));
 } finally { await browser.close(); }
})().catch(e=>{console.error(JSON.stringify({base:BASE,results},null,2)); process.exit(1);});
