/* Saved exact live regression: no inference calls. */
const {chromium}=require('playwright');
const {assert,assertionCount}=require('./assertions.cjs');
const fs=require('node:fs');
(async()=>{
  const project=JSON.parse(fs.readFileSync('examples/live-microgrids.json','utf8'));
  const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8000');
  await page.locator('#projects .project-link, #projects .hint').first().waitFor();
  await page.evaluate(id=>localStorage.setItem('northstar-project',id),project.id);await page.reload();
  await page.getByRole('heading',{name:'Confirmed requirements',exact:true}).waitFor();
  assert.match(await page.locator('#content').innerText(),/365 days.*\$2,500,000.*12 people.*10 solar microgrids.*Haiti/);
  assert.match(await page.locator('#content').innerText(),/200 days/);
  assert.match(await page.locator('#content').innerText(),/\$2,171,600/);
  await page.screenshot({path:'docs/screenshots/live-microgrids.png',fullPage:true});
  for(const view of ['Work breakdown','Timeline','Budget & resources','Risks','Agent activity','Scenarios','Knowledge','Export']){
    await page.locator(`[data-view="${view}"]`).click();
    assert((await page.locator('#content').innerText()).length>100);
  }
  await page.locator('[data-view="Risks"]').click();
  assert.match(await page.locator('#content').innerText(),/Subjective estimate/);
  assert.match(await page.locator('#content').innerText(),/Consistent/);
  await page.screenshot({path:'docs/screenshots/live-microgrid-review.png',fullPage:true});
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log(JSON.stringify({status:'passed',assertions:assertionCount(),pageErrors:0,liveInferenceRequests:0}));
})().catch(e=>{console.error(e.message);process.exit(1);});
