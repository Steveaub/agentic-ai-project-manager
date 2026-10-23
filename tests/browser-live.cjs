/* Inspects saved REAL live runs without consuming additional inference quota. */
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {assert,assertionCount}=require('./assertions.cjs');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',err=>errors.push(err.message));
  const projectId=process.env.LIVE_PROJECT_ID;
  assert(projectId,'Set LIVE_PROJECT_ID to a verified saved live run');
  await page.goto('http://127.0.0.1:8000');
  await page.locator('#projects .project-link, #projects .hint').first().waitFor();
  await page.evaluate(id=>localStorage.setItem('northstar-project',id),projectId);
  await page.reload();
  await page.getByRole('heading',{name:'The path to launch'}).waitFor();
  assert.equal(await page.locator('#mode').innerText(),'LIVE MODEL OUTPUT');
  assert.match(await page.locator('#heading').innerText(),/solar|wi.?fi/i);
  fs.mkdirSync('docs/screenshots',{recursive:true});
  await page.screenshot({path:'docs/screenshots/live-solar.png',fullPage:true});
  for(const view of ['Work breakdown','Timeline','Budget & resources','Risks','Scenarios','Knowledge','Agent activity','Export']){
    await page.locator(`[data-view="${view}"]`).click();
    assert((await page.locator('#content').innerText()).length>100);
  }
  await page.locator('[data-view="Agent activity"]').click();
  const activity=await page.locator('#content').innerText();
  assert.match(activity,/gemini/i);assert.match(activity,/groq/i);assert.match(activity,/openrouter/i);
  assert.match(activity,/pydantic_valid/);
  await page.screenshot({path:'docs/screenshots/live-agent-activity.png',fullPage:true});
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log(JSON.stringify({status:'passed',assertions:assertionCount(),pageErrors:0,liveInferenceRequests:0}));
})().catch(err=>{console.error(err);process.exit(1);});
