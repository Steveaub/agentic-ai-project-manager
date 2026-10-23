/* Explicit manual live evaluation. Consumes confirmed free quota; never part of CI. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8000');
  await page.waitForSelector('#projects .hint, #projects button');
  await page.locator('#goal').fill('Organize a regional technology conference for 250 attendees, with speakers, sponsors, an accessible venue, registration and AV, within 120 days and a $75000 budget.');
  await page.locator('#days').fill('120');await page.locator('#budget').fill('75000');await page.locator('#team').fill('5');
  await page.locator('#provider').selectOption('multi');
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST',{timeout:310000});
  await page.getByRole('button',{name:'Build execution plan'}).click();
  await page.locator('#requirements-dialog[open]').waitFor();
  await page.locator('#requirements-agreed').check();
  await page.getByRole('button',{name:'Confirm and generate plan'}).click();
  const response=await responsePromise;
  const project=await response.json();
  if(response.status()!==201)throw new Error(JSON.stringify({status:response.status(),detail:project.detail}));
  await page.getByRole('heading',{name:'The path to launch'}).waitFor();
  const revision=project.revisions.at(-1);
  assert.equal(revision.provider,'multi');assert.equal(revision.trace.length,5);
  assert.match(revision.plan.tasks.map(t=>t.title).join(' '),/speaker|venue|conference|registration/i);
  assert.equal(await page.locator('#mode').innerText(),'LIVE MODEL OUTPUT');
  fs.mkdirSync('data',{recursive:true});fs.mkdirSync('docs/screenshots',{recursive:true});
  const record={scenario:'conference_browser',status:'passed',project_id:project.id,revision:1,
    title:revision.plan.title,tasks:revision.plan.tasks.length,days:revision.results.schedule.days,
    cost:revision.results.budget.total,review:revision.results.review,execution:revision.results.execution,
    pageErrors:errors.length};
  fs.appendFileSync('data/live-validation.jsonl',JSON.stringify(record)+'\n');
  fs.writeFileSync('data/live-browser-project.json',JSON.stringify(project,null,2));
  await page.screenshot({path:'docs/screenshots/live-conference.png',fullPage:true});
  await page.locator('[data-view="Agent activity"]').click();
  await page.screenshot({path:'docs/screenshots/live-conference-activity.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify(record,null,2));
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
