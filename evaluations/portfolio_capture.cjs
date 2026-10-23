/* Saved receipt replay only; run against the prepared portfolio database. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');await page.locator('#projects .project-link').first().waitFor();
 assert.equal(await page.locator('#projects .project-link').count(),2,'Use the isolated two-receipt portfolio database');
 await page.locator('[data-project="a90b31a1ba9540868e7ddd3261168ee6"]').click();
 await page.getByRole('heading',{name:'Confirmed requirements',exact:true}).waitFor();
 await page.screenshot({path:'docs/screenshots/portfolio-overview.png'});
 await page.locator('[data-view="Budget & resources"]').click();
 await page.getByRole('heading',{name:'Cost categories and estimate evidence'}).locator('..').screenshot({path:'docs/screenshots/portfolio-costs.png'});
 await page.setViewportSize({width:390,height:844});
 for(const view of ['Overview','Work breakdown','Agent activity','Budget & resources','Timeline']){
  await page.locator(`[data-view="${view}"]`).click();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 }
 await page.locator('[data-view="Overview"]').click();await page.locator('header').scrollIntoViewIfNeeded();
 await page.screenshot({path:'docs/screenshots/portfolio-mobile.png'});
 await page.setViewportSize({width:1440,height:1000});
 await page.locator('[data-project="94864088a4af4283af42124141c6150d"]').click();
 await page.locator('[data-view="Risks"]').click();
 await page.getByRole('heading',{name:'Independent model opinion'}).locator('..').screenshot({path:'docs/screenshots/portfolio-review.png'});
 await page.locator('[data-view="Agent activity"]').click();await page.locator('header').scrollIntoViewIfNeeded();
 await page.screenshot({path:'docs/screenshots/portfolio-activity.png'});
 assert.deepEqual(errors,[]);
 await browser.close();console.log(JSON.stringify({status:'passed',savedReceiptReplay:true,liveInferenceRequests:0,screenshots:5}));
})().catch(e=>{console.error(e.message);process.exit(1);});
