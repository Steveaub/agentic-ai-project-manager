/* Run against localhost:8000. PLAYWRIGHT_MODULE may point at a bundled install. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const {assert,assertionCount}=require('./assertions.cjs');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.BROWSER_CHANNEL ? {channel:process.env.BROWSER_CHANNEL} : {})});
  const page = await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',err=>errors.push(err.message));
  const shots=process.env.SCREENSHOT_DIR || 'docs/screenshots';
  fs.mkdirSync(shots,{recursive:true});
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('button',{name:'Build execution plan'}).click();
  await page.getByRole('heading',{name:'The path to launch'}).waitFor();
  assert.match(await page.locator('#content').innerText(),/\$16,270/);
  await page.screenshot({path:`${shots}/dashboard.png`,fullPage:true});

  for(const name of ['Work breakdown','Timeline','Budget & resources','Risks','Agent activity','Export']) {
    await page.locator(`[data-view="${name}"]`).click();
    assert((await page.locator('#content').innerText()).length>100);

  }
  await page.locator('[data-view="Knowledge"]').click();
  await page.locator('#document-file').setInputFiles({name:'fictional-charter.md',mimeType:'text/markdown',buffer:Buffer.from('Payment requirements: test checkout in the sandbox before launch. Confirm product catalog acceptance.')});
  await page.getByRole('button',{name:'Index document',exact:true}).click();
  await page.getByText(/Indexed 1 chunks/).waitFor();
  await page.getByRole('button',{name:'Search knowledge',exact:true}).click();
  await page.locator('#search-result .source').waitFor();
  assert.match(await page.locator('#search-result').innerText(),/test checkout/);
  await page.locator('[data-view="Scenarios"]').click();
  await page.locator('#scenario-days').fill('46');
  await page.locator('#scenario-budget').fill('15000');
  await page.getByRole('button',{name:'Preview scenario',exact:true}).click();
  await page.getByRole('heading',{name:'Scenario comparison',exact:true}).waitFor();
  assert.match(await page.locator('#scenario-result').innerText(),/\$1,270/);
  await page.screenshot({path:`${shots}/scenario.png`,fullPage:true});
  await page.getByRole('button',{name:'Save as new revision',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('#revision-select option').length===2);
  await page.locator('#revision-select').selectOption('0');
  await page.locator('[data-view="Overview"]').click();
  assert.match(await page.locator('#content').innerText(),/Within limits/);
  await page.reload();
  await page.waitForFunction(()=>document.querySelectorAll('#revision-select option').length===2);
  await page.locator('[data-view="Export"]').click();
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('link',{name:'Download tasks CSV',exact:true}).click();
  const download=await downloadPromise;
  assert.equal(download.suggestedFilename(),'tasks.csv');
  await page.locator('[data-view="Overview"]').click();
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:`${shots}/mobile.png`,fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'passed',assertions:assertionCount(),browser:'Chromium',pageErrors:errors.length}));
  await browser.close();
})().catch(err=>{console.error(err);process.exit(1);});
