const {chromium}=require('playwright');
const {assert,assertionCount}=require('./assertions.cjs');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:process.env.BROWSER_CHANNEL||'chrome'});
 const page=await browser.newPage({viewport:{width:1363,height:850}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8000');
 await page.locator('#projects .project-link, #projects .hint').first().waitFor();
 const create=async()=>{const response=await page.request.post('http://127.0.0.1:8000/api/projects',{data:{goal:{objective:'Explicit browser deletion test project'}}});assert.equal(response.status(),201);return response.json();};
 const a=await create(),b=await create();
 await page.reload();
 await page.locator(`[data-project="${a.id}"]`).click();
 await page.getByRole('heading',{name:'The path to launch'}).waitFor();
 await page.locator('[data-view="Scenarios"]').click();
 assert.equal(await page.locator('#scenario-budget').inputValue(),'20000');
 assert.equal(await page.locator('#scenario-days').inputValue(),'60');
 assert(!(await page.locator('#change').inputValue()).includes('15,000'));
 await page.locator(`[data-delete="${a.id}"]`).click();
 await page.locator('#delete-dialog[open]').waitFor();
 assert.match(await page.locator('#delete-dialog').innerText(),/cannot be undone/);
 await page.locator('#cancel-delete').click();
 assert.equal((await page.request.get('http://127.0.0.1:8000/api/projects/'+a.id)).status(),200);
 await page.locator(`[data-delete="${a.id}"]`).click();
 await page.getByRole('button',{name:'Permanently delete this project',exact:true}).click();
 await page.locator('#delete-dialog').waitFor({state:'hidden'});
 assert.equal((await page.request.get('http://127.0.0.1:8000/api/projects/'+a.id)).status(),404);
 assert(await page.locator('#create-view').isVisible());
 assert.equal(await page.evaluate(()=>localStorage.getItem('northstar-project')),null);
 assert.equal((await page.request.get('http://127.0.0.1:8000/api/projects/'+b.id)).status(),200);
 // Delete only the second record created by this test; unrelated saved data stays untouched.
 await page.locator(`[data-delete="${b.id}"]`).click();await page.getByRole('button',{name:'Permanently delete this project',exact:true}).click();
 await page.locator('#delete-dialog').waitFor({state:'hidden'});
 for(const size of [{width:1363,height:727},{width:390,height:844}]){
  await page.setViewportSize(size);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert(await page.locator('#new-project').isVisible());
  assert.equal(await page.locator('#projects').evaluate(el=>getComputedStyle(el.closest('.saved')).display),'block');
 }
 const fixture=JSON.parse(fs.readFileSync('examples/live-haiti-expanded.json','utf8'));
 await page.route('**/api/projects/mobile-fixture',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(fixture)}));
 await page.evaluate(()=>localStorage.setItem('northstar-project','mobile-fixture'));await page.reload();
 await page.getByRole('heading',{name:'Confirmed requirements',exact:true}).waitFor();
 for(const size of [{width:1363,height:727},{width:390,height:844}]){
  await page.setViewportSize(size);
  for(const view of ['Overview','Agent activity','Budget & resources','Work breakdown','Timeline']){
   await page.locator(`[data-view="${view}"]`).click();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  }
 }
 await page.locator('#new-project').click();
 await page.locator('#goal').fill(fixture.goal.objective);await page.locator('#provider').selectOption('multi');
 await page.getByRole('button',{name:'Build execution plan'}).click();await page.locator('#requirements-dialog[open]').waitFor();
 assert.equal(await page.locator('#confirmed-days').inputValue(),'365');
 assert.equal(await page.locator('#confirmed-budget').inputValue(),'2500000');
 assert.equal(await page.locator('#confirmed-team').inputValue(),'12');
 assert.match(await page.locator('#requirements-summary').innerText(),/10 solar-powered community microgrids.*Haiti/);
 assert.match(await page.locator('#requirements-summary').innerText(),/100 households/);
 await page.locator('#cancel-confirmation').click();
 assert.deepEqual(errors,[]);
 await browser.close();console.log(JSON.stringify({status:'passed',assertions:assertionCount(),pageErrors:0,liveInferenceRequests:0}));
})().catch(e=>{console.error(e.message);process.exit(1);});
