'use strict';
const $ = (s) => document.querySelector(s);
const escapeHTML = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const e = escapeHTML;
const money = (n) => new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
let project = null, revisionIndex = 0, view = 'Overview', scenario = null, providerSettings = null;
const views = [['Overview','◫'],['Work breakdown','▤'],['Timeline','↗'],['Budget & resources','$'],['Risks','◇'],['Scenarios','⇄'],['Knowledge','▧'],['Agent activity','✳'],['Export','↓']];
$('#nav').innerHTML = views.map(([name,icon])=>`<button data-view="${name}"><span>${icon}</span>${name}</button>`).join('');
async function api(path, data) {
  const response = await fetch('/api'+path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.message || JSON.stringify(body.detail));
  return body;
}
async function action(fn) {
  $('#error').hidden = true; $('#busy').hidden = false;
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try { await fn(); } catch (err) { $('#error').textContent=err.message; $('#error').hidden=false; $('#confirmation-error').textContent=err.message; $('#confirmation-error').hidden=false; }
  finally { $('#busy').hidden=true; document.querySelectorAll('button').forEach(b=>b.disabled=false); }
}
async function loadProjects() {
  const list = await api('/projects');
  $('#projects').innerHTML=list.map(p=>`<button class="project-link" data-project="${e(p.id)}">${e(p.title)}</button>`).join('') || '<p class="hint">Your plans will appear here.</p>';
}
function current() { return project.revisions[revisionIndex]; }
function showProject(p) {
  project=p; revisionIndex=p.revisions.length-1; scenario=null;
  localStorage.setItem('northstar-project',p.id);
  $('#create-view').hidden=true; $('#project-view').hidden=false; render();
}
function metric(label,value,note,cls='') { return `<div class="metric"><span class="label">${e(label)}</span><strong class="${cls}">${e(value)}</strong><small>${e(note)}</small></div>`; }
function list(items) { return `<ul class="bullet">${items.map(i=>`<li>${e(i)}</li>`).join('')}</ul>`; }
function technicalDetails(value) { return `<details class="technical-details"><summary>Technical details · JSON</summary><pre>${e(JSON.stringify(value,null,2))}</pre></details>`; }
function namedList(title,items) { return items?.length?`<h3>${e(title)}</h3>${list(items)}`:''; }
function reviewHTML(review) {
  if(review.source==='unavailable') return `<p>${e(review.message)}</p>`;
  const kinds={subjective_estimate:'Subjective estimate',semantic_gap:'Scope or deliverable concern',requirements_inconsistency:'Requirements inconsistency'};
  return `${review.summary?`<p>${e(review.summary)}</p>`:''}${review.verdict?`<p><strong>Reviewer verdict:</strong> ${review.verdict==='consistent'?'Consistent with confirmed requirements':'Corrections required'}</p>`:''}${(review.findings||[]).map(f=>`<article class="risk"><span class="badge">${e(f.severity)} · ${e(kinds[f.kind]||f.kind)}</span><p>${e(f.message)}</p><p><strong>Recommended correction:</strong> ${e(f.recommended_correction)}</p></article>`).join('')}${namedList('Coverage concerns',review.coverage_gaps)}${namedList('Estimate concerns',review.estimate_concerns)}${namedList('Recommendations',review.recommendations)}${technicalDetails(review)}`;
}
function decisionHTML(message) {
  let value;
  try { value=JSON.parse(message); } catch {
    const start=String(message).indexOf('{');
    if(start>0){try{JSON.parse(message.slice(start));return `<p>${e(message.slice(0,start))}</p>${decisionHTML(message.slice(start))}`;}catch{ /* Plain narrative stays escaped. */ }}
    return `<p>${e(message)}</p>`;
  }
  if(!value || typeof value!=='object') return `<p>${e(String(value))}</p>`;
  if(Array.isArray(value.requirements)) return namedList('Requirements',value.requirements)+namedList('Assumptions',value.assumptions)+namedList('Open questions',value.questions)+technicalDetails(value);
  if(typeof value.feasible==='boolean') return `<p><strong>${value.feasible?'Within budget and deadline':'Outside budget or deadline'}</strong></p>${namedList('Calculated findings',value.findings)}<p class="hint">${e(value.verified||'')}</p>${technicalDetails(value)}`;
  if(value.source==='ai_opinion' || value.coverage_gaps || (value.summary && Array.isArray(value.findings))) return reviewHTML(value);
  return `<p>Structured execution record available below.</p>${technicalDetails(value)}`;
}
function costEvidenceHTML(r) {
  const b=r.results.budget, rate=r.results.estimation;
  const categories=b.categories||{};
  const labels={labor:'Labor',equipment:'Equipment',materials:'Materials',logistics:'Logistics',permitting:'Permitting',contingency:'Contingency'};
  const categoryRows=Object.entries(labels).map(([key,label])=>`<tr><td>${label}</td><td>${typeof categories[key]==='number'?money(categories[key]):'Not itemized'}</td></tr>`).join('');
  return `<section class="panel"><h2>Cost categories and estimate evidence</h2><div class="table-wrap"><table><thead><tr><th>COST CATEGORY</th><th>ESTIMATED USD</th></tr></thead><tbody>${categoryRows}${b.unclassified_fixed?`<tr><td>Fixed costs without category detail</td><td>${money(b.unclassified_fixed)}</td></tr>`:''}<tr><th>Total estimated cost</th><th>${money(b.total)}</th></tr></tbody></table></div><p class="hint">${e(b.estimate_status||'Estimates require human validation.')}</p>${rate?`<h3>Labor-rate basis</h3><p><strong>${e(new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(rate.daily_rate))} per person per planning day</strong></p><p>${e(rate.basis)}</p><p>${rate.budget_withheld?'The available budget was withheld from the labor-rate estimate.':'Budget independence was not recorded.'}</p><p class="hint">${e(rate.status||'Unverified estimate; obtain independent quotes.')}</p>`:'<p>Independent labor-rate evidence was not recorded for this revision.</p>'}${namedList('Missing or excluded cost categories',(b.category_exclusions||[]).map(item=>`${labels[item.category]||item.category}: ${item.reason}`))}${namedList('Estimate notes',r.plan.estimation_notes)}${technicalDetails({categories:b.categories,unclassified_fixed:b.unclassified_fixed,category_exclusions:b.category_exclusions,labor_estimate:rate})}</section>`;
}
function coverageHTML(r) {
  const scope=r.results.confirmed_requirements?.scope||r.plan.scope;
  const rows=(r.plan.requirement_coverage||[]).map(item=>{
    const requirement=scope?.deliverables.find(q=>q.id===item.requirement_id);
    return `<tr><td>${e(item.requirement_id)} · ${e(requirement?.description||'Requirement')}</td><td>${e(item.task_ids.join(', ')||'No tasks assigned')}</td><td>${e(item.exclusion_reason||'Included')}</td></tr>`;
  }).join('');
  return `<section class="panel"><h2>Coverage and explicit exclusions</h2>${rows?`<div class="table-wrap"><table><thead><tr><th>REQUIREMENT</th><th>WORK PACKAGES</th><th>SCOPE STATUS</th></tr></thead><tbody>${rows}</tbody></table></div>`:'<p>Requirement coverage was not recorded for this revision.</p>'}${namedList('Exclusions',r.plan.exclusions?.length?r.plan.exclusions:['No exclusions declared; confirm scope boundaries before execution.'])}<p class="hint">Coverage links are checked deterministically. Substantive coverage receives independent review when that workflow is selected.</p>${technicalDetails(r.plan.requirement_coverage||[])}</section>`;
}
function taskTable(r) {
  const s=Object.fromEntries(r.results.schedule.tasks.map(t=>[t.id,t]));
  return `<div class="table-wrap"><table><thead><tr><th>WORK PACKAGE</th><th>GROUP / WBS</th><th>DAYS</th><th>DEPENDENCIES</th><th>PATH</th></tr></thead><tbody>${r.plan.tasks.map(t=>`<tr><td>${e(t.title)}<small>${e(t.id)} · ${e(t.source)}</small></td><td>${e(t.deliverable)}</td><td>${t.duration}</td><td>${e(r.plan.dependencies.filter(d=>d.successor===t.id).map(d=>d.predecessor).join(', ')||'—')}</td><td><span class="pill ${s[t.id].critical?'critical':''}">${s[t.id].critical?'Critical':'Float '+s[t.id].float+'d'}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function timeline(r) {
  const tasks=Object.fromEntries(r.plan.tasks.map(t=>[t.id,t])); const scale=Math.max(r.constraints.days,r.results.schedule.days);
  return `<div class="timeline"><div class="timeline-scale"><span>Day 0</span><span>Day ${Math.round(scale/2)}</span><span>Day ${scale}</span></div>${r.results.schedule.tasks.map(t=>`<div class="timeline-row"><span>${e(t.id)} · ${e(tasks[t.id].title)}</span><div class="track"><span class="bar ${t.critical?'critical':''}" style="left:${100*t.start/scale}%;width:${100*(t.end-t.start)/scale}%" title="Day ${t.start} to ${t.end}; float ${t.float} days">${t.start}–${t.end}</span></div></div>`).join('')}</div>`;
}
function render() {
  if(!project) return;
  const r=current(), s=r.results.schedule, b=r.results.budget, resource=r.results.resources;
  $('#heading').textContent=r.plan.title; $('#mode').textContent=r.provider==='demo'?'NO-COST DEMO':'LIVE MODEL OUTPUT';
  $('#nav').querySelectorAll('button').forEach(btn=>btn.classList.toggle('active',btn.dataset.view===view));
  $('#revision-bar').innerHTML=`<div class="revision-bar"><span>${e(project.goal.objective)}</span><label>Saved revision <select id="revision-select">${project.revisions.map((rev,i)=>`<option value="${i}" ${i===revisionIndex?'selected':''}>v${rev.number} · ${e(new Date(rev.created_at).toLocaleString())}</option>`).join('')}</select></label></div>`;
  const warnings=r.results.review.findings;
  const banner=`${r.provider==='demo'?'<div class="callout">Demo mode · Fictional e-commerce fixture. No model was called. Estimates are illustrative; calculations use the numeric constraints.</div>':''}${warnings.length?`<div class="callout warning">${warnings.map(e).join('<br>')}</div>`:''}`;
  let html='';
  if(view==='Overview') html=`${banner}<div class="metrics">${metric('Resource-leveled duration',s.days+' days',s.slack_days>=0?s.slack_days+' days before target':-s.slack_days+' days over target',s.feasible?'ok':'warn')}${metric('Estimated project cost',money(b.total),'of '+money(b.limit)+' budget',b.feasible?'ok':'warn')}${metric('Team capacity',r.constraints.team_size+' people',resource.person_days+' estimated person-days')}${metric('Plan feasibility',r.results.review.feasible?'Within limits':'Needs a decision','Calculated against stated constraints',r.results.review.feasible?'ok':'warn')}</div><div class="two-col"><section class="panel"><div class="section-head"><h2>The path to launch</h2><span class="pill">${r.plan.tasks.length} work packages</span></div><p class="subtitle">Resource-leveled schedule · green bars mark CPM-critical work</p>${timeline(r)}</section><section class="panel"><h2>Milestone checkpoints</h2>${s.milestones.map(m=>`<div class="milestone"><div class="day">DAY<strong>${m.day}</strong></div><span>${e(m.title)}</span></div>`).join('')}<p class="hint">Targets are calculated from estimated work, not guaranteed delivery dates.</p></section></div><section class="panel"><h2>Decisions before execution</h2>${list(r.plan.questions)}</section>`;
  if(view==='Work breakdown') html=`<section class="panel"><h2>Work breakdown structure</h2><p class="subtitle">Deliverable groups → leaf work packages. Finish-to-start dependencies; no summary-task scheduling.</p>${taskTable(r)}</section><section class="panel"><h2>Explicit assumptions</h2>${list(r.plan.assumptions)}</section>`;
  if(view==='Timeline') html=`${banner}<section class="panel"><h2>Execution timeline</h2><p class="subtitle">${e(s.method)}. CPM lower bound: ${s.cpm_days} days. Critical tasks may form multiple paths.</p>${timeline(r)}<p class="hint">Dependency relationships are listed below. Float is calculated before resource leveling.</p>${taskTable(r)}</section>`;
  if(view==='Budget & resources') html=`<div class="metrics">${metric('Calculated total',money(b.total),'USD · based on task estimates')}${metric('Budget headroom',money(b.remaining),'No automatic reductions',b.feasible?'ok':'warn')}${metric('Allocated effort',resource.person_days+' pd','People × duration')}${metric('Deadline utilization',Math.round(resource.deadline_utilization*100)+'%',resource.capacity_person_days+' person-days available')}</div><section class="panel"><h2>Cost breakdown</h2><p class="subtitle">${e(b.basis)}</p><div class="table-wrap"><table><thead><tr><th>TASK</th><th>DAILY RATE / PERSON</th><th>LABOR</th><th>FIXED</th><th>TOTAL</th></tr></thead><tbody>${b.items.map(item=>{const task=r.plan.tasks.find(t=>t.id===item.task_id);return `<tr><td>${e(task.title)}<small>${e(task.source)}</small></td><td>${money(task.daily_rate)}</td><td>${money(item.labor)}</td><td>${money(item.fixed)}</td><td>${money(item.total)}</td></tr>`;}).join('')}</tbody></table></div></section><section class="panel"><h2>Daily resource allocation</h2><div class="utilization" role="img" aria-label="Daily pooled team allocation; peak ${resource.peak_people} people">${s.daily_people.map((p,i)=>`<i title="Day ${i}: ${p} people" style="height:${100*p/r.constraints.team_size}%"></i>`).join('')}</div><p class="hint">${e(resource.assumption)}. Peak ${resource.peak_people} of ${r.constraints.team_size} people.</p></section>`;
  if(view==='Risks') html=`<section class="panel"><h2>Risk register</h2><p class="subtitle">Estimates and calculated constraint exceptions are labeled separately.</p>${warnings.map(w=>`<div class="risk"><span class="badge">CALCULATED CONSTRAINT EXCEPTION</span><p>${e(w)}</p><p>Decision needed: renegotiate deadline, budget or scope; validate changes with the team.</p></div>`).join('')}${r.plan.risks.map(risk=>`<div class="risk"><h3>${e(risk.title)}</h3><span class="badge">${e(risk.probability)} probability / ${e(risk.impact)} impact</span><p>${e(risk.mitigation)}</p><span class="pill">${e(risk.source)}</span></div>`).join('')}</section>`;
  if(view==='Scenarios') html=`<section class="panel"><h2>What changes when constraints change?</h2><p class="subtitle">Scenarios use the latest saved revision. Preview does not save; commit appends a revision and retains the original.</p><form id="scenario-form"><div class="form-grid"><label>Target days<input id="scenario-days" type="number" min="1" max="3650" value="${Math.max(1,project.revisions.at(-1).constraints.days-14)}" required></label><label>Budget · USD<input id="scenario-budget" type="number" min="1" max="1000000000" value="${project.revisions.at(-1).constraints.budget}" required></label><label>Team members<input id="scenario-team" type="number" min="1" max="100" value="${project.revisions.at(-1).constraints.team_size}" required></label></div><label>Change request<textarea id="change" rows="2" maxlength="2000">Adjust the project constraints while preserving approved scope. Identify feasibility changes and tradeoffs.</textarea></label><div class="actions"><button class="primary" type="submit">Preview scenario</button><button class="secondary" type="button" id="commit-scenario">Save as new revision</button></div><p class="hint">Uses the latest revision's provider. In live mode, preview and save each consume free quota separately. Demo revisions retain all work estimates and report infeasibility honestly.</p></form></section><div id="scenario-result">${scenario?scenarioHTML(scenario):''}</div>`;
  if(view==='Knowledge') html=`<div class="two-col"><section class="panel"><h2>Project knowledge</h2><p class="subtitle">Upload UTF-8 .txt or .md documents. Stored as overlapping chunks and normalized lexical vectors in SQLite.</p><form id="document-form"><label>Document file<input type="file" id="document-file" accept=".txt,.md,text/plain,text/markdown" required></label><button class="primary" type="submit">Index document</button></form><p class="hint">100,000 characters per document; 500 chunks per project. Upload fictional or non-sensitive data. Documents are untrusted reference material. Live revisions send matching excerpts to the model; demo mode attaches them for human review.</p><div id="document-status" role="status"></div></section><section class="panel"><h2>Find supporting passages</h2><form id="search-form"><label>Query<input id="query" value="payment requirements" required maxlength="2000"></label><button class="secondary" type="submit">Search knowledge</button></form><p class="hint">Cosine similarity over local word-hash vectors. This is lexical retrieval; pretrained semantic embeddings are not implemented.</p><div id="search-result"></div></section></div><section class="panel"><h2>Sources used in this revision</h2>${sourcesHTML(r.sources)}</section>`;
  if(view==='Agent activity') html=`<section class="panel"><h2>Execution record</h2><p class="subtitle">Completed actions, not a simulated live stream. ${r.results.execution.model_calls} actual model calls; ${r.results.execution.reported_tokens} reported tokens. Prompt ${e(r.results.execution.prompt_version)}.</p>${r.decisions.map(d=>`<article class="trace"><h3>${e(d.agent)}</h3>${decisionHTML(d.message)}<small>${e(new Date(d.timestamp).toLocaleString())}</small></article>`).join('')}${r.trace.map(t=>`<article class="trace"><h3>Tool · ${e(t.tool)} <span class="pill">${e(t.status)} · ${t.duration_ms} ms</span></h3><details><summary>Inspect calculated output</summary><pre>${e(JSON.stringify(t.output,null,2))}</pre></details></article>`).join('')}</section>`;
  if(view==='Export') html=`<section class="panel"><h2>Take the plan with you</h2><p class="subtitle">Export the latest saved project. JSON includes all revisions, traces, assumptions and retrieved excerpts. CSV contains the current task schedule and costs.</p><div class="actions"><a class="primary" href="/api/projects/${project.id}/export?format=json" download>Download project JSON</a><a class="secondary" href="/api/projects/${project.id}/export?format=csv" download>Download tasks CSV</a></div></section><section class="panel"><h2>Change history</h2>${project.revisions.map(rev=>`<article class="trace"><h3>Revision ${rev.number}</h3><p>${e(rev.change)}</p><p>${rev.constraints.days} days · ${money(rev.constraints.budget)} budget · ${rev.constraints.team_size} people</p></article>`).join('')}</section>`;
  if(view==='Agent activity' && r.results.execution.invocations) {
    const execution=r.results.execution;
    html=`<section class="panel"><h2>Live provider invocations</h2><p class="subtitle">Actual completed requests · ${Math.round(execution.duration_ms/1000)} seconds · ${e(execution.workflow_outcome)}. Token counts are provider-reported; missing counts are unavailable.</p>${execution.invocations.map(i=>`<article class="trace"><h3>${e(i.role)} · ${e(i.provider)}</h3><p>${e(i.model)} · ${e(i.status)} · ${i.duration_ms} ms</p><p>Validation: ${e(i.validation)} · Input ${i.input_tokens??'unavailable'} / output ${i.output_tokens??'unavailable'} tokens</p>${i.error?`<p>${e(i.error)}</p>`:''}<small>Request ${e(i.request_id||'unavailable')}</small></article>`).join('')}<button class="secondary" id="load-failures">Show failed execution history</button><div id="failed-executions"></div></section>`+html;
  }
  if(view==='Risks' && r.results.independent_review) html+=`<section class="panel"><h2>Independent model opinion</h2><p class="subtitle">Model judgments are separate from calculated feasibility.</p>${reviewHTML(r.results.independent_review)}</section>`;
  if(r.provider!=='demo') {
    const authority=r.results.confirmed_requirements;
    html=(authority?`<section class="panel"><h2>Confirmed requirements</h2><p>${authority.constraints.days} days · ${money(authority.constraints.budget)} · ${authority.constraints.team_size} people · ${authority.scope.quantity} ${e(authority.scope.asset)} · ${e(authority.scope.location)}</p><p>Requirements validation: ${r.results.acceptance?.status==='passed'?'passed':e(r.results.acceptance?.status||'not recorded')}. ${r.results.review.feasible?'Calculated estimates are within budget and deadline.':'The estimate exceeds the confirmed budget or deadline; a decision is required.'} Preliminary estimates; delivery is not verified.${r.results.acceptance?.independent_review_required===false?' Independent model review was not run for this workflow.':''}</p></section>`:'<div class="callout warning">Historical live plan: confirmed requirements and current acceptance checks were not recorded. Create a newly confirmed plan before relying on it.</div>')+html;
  }
  if(view==='Budget & resources') html+=costEvidenceHTML(r);
  if(view==='Work breakdown') html+=coverageHTML(r);
  $('#content').innerHTML=html;
}
function sourcesHTML(sources) { return sources.length?sources.map(s=>`<article class="source"><strong>${e(s.name)} · chunk ${s.chunk+1}</strong><small> · similarity ${s.score}</small><p>${e(s.text)}</p></article>`).join(''):'<p class="empty">No matching source passages for this revision.</p>'; }
function scenarioHTML(value) {const a=value.baseline, b=value.scenario;return `<section class="panel"><h2>Scenario comparison</h2><table><thead><tr><th>MEASURE</th><th>SAVED BASELINE</th><th>PROPOSED</th></tr></thead><tbody><tr><td>Target days</td><td>${a.constraints.days}</td><td>${b.constraints.days}</td></tr><tr><td>Calculated days</td><td>${a.results.schedule.days}</td><td>${b.results.schedule.days}</td></tr><tr><td>Budget limit</td><td>${money(a.constraints.budget)}</td><td>${money(b.constraints.budget)}</td></tr><tr><td>Estimated cost</td><td>${money(a.results.budget.total)}</td><td>${money(b.results.budget.total)}</td></tr><tr><td>Within constraints</td><td>${a.results.review.feasible?'Yes':'No'}</td><td>${b.results.review.feasible?'Yes':'No'}</td></tr></tbody></table><div class="callout warning">${b.results.review.findings.length?b.results.review.findings.map(e).join('<br>'):'Within stated constraints; estimates still require human review.'}</div><p class="hint">Original tasks retain stable IDs. Tighter constraints alone do not reduce effort or costs.</p></section>`;}
function scenarioInput() {return {constraints:{days:+$('#scenario-days').value,budget:+$('#scenario-budget').value,team_size:+$('#scenario-team').value},change:$('#change').value,provider:project.revisions.at(-1).provider,expected_revision:project.revisions.length};}
let pendingConfirmation = null;
function presentConfirmation(draft, finish) {
  $('#confirmation-error').hidden=true;
  pendingConfirmation={draft,finish};
  const labels={days:'Target days',budget:'Budget',team_size:'Team members'};
  const formatted=(field,value)=>field==='budget'?money(value):String(value);
  const conflicts=draft.conflicts.map(c=>c.kind==='form_differs'?`${labels[c.field]}: request ${formatted(c.field,c.request_value)}; form proposal ${formatted(c.field,c.form_value)}. The request value is proposed for confirmation.`:`${labels[c.field]}: conflicting request values ${c.values.map(v=>formatted(c.field,v)).join(' or ')}. Choose a value and explain the resolution.`);
  $('#requirements-summary').innerHTML=`<h3>${e(draft.scope.quantity)} ${e(draft.scope.asset)} · ${e(draft.scope.location)}</h3>${list(draft.scope.deliverables.map(r=>r.id+' · '+r.description+(r.mandatory?' (mandatory)':'')))}<h3>Conflicts to review</h3>${conflicts.length?list(conflicts):'<p>No conflicting values detected.</p>'}<h3>Open questions</h3>${list(draft.questions)}<details><summary>Extraction evidence</summary><pre>${e(JSON.stringify(draft.provenance,null,2))}</pre></details>`;
  $('#confirmed-days').value=draft.proposed_constraints.days??'';
  $('#confirmed-budget').value=draft.proposed_constraints.budget??'';
  $('#confirmed-team').value=draft.proposed_constraints.team_size??'';
  $('#confirmation-resolution').value=''; $('#requirements-agreed').checked=false;
  $('#requirements-dialog').showModal();
}
$('#cancel-confirmation').addEventListener('click',()=>{$('#requirements-dialog').close();pendingConfirmation=null;});
$('#confirmation-form').addEventListener('submit',ev=>{ev.preventDefault();action(async()=>{
  const pending=pendingConfirmation;
  const authority=await api('/requirements/confirm',{draft_id:pending.draft.id,confirmed:true,
    constraints:{days:+$('#confirmed-days').value,budget:+$('#confirmed-budget').value,team_size:+$('#confirmed-team').value},
    scope:pending.draft.scope,resolution:$('#confirmation-resolution').value});
  $('#requirements-dialog').close();pendingConfirmation=null;
  await pending.finish(authority);
});});
$('#create-form').addEventListener('submit',ev=>{ev.preventDefault();action(async()=>{
  const body={goal:{objective:$('#goal').value},provider:$('#provider').value};
  if(body.provider==='demo') body.constraints={days:+$('#days').value,budget:+$('#budget').value,team_size:+$('#team').value};
  const finish=async authority=>{if(authority){body.constraints=authority.constraints;body.confirmation_id=authority.id;}
    const p=await api('/projects',body);view='Overview';showProject(p);await loadProjects();};
  if(body.provider==='demo') await finish(null);
  else presentConfirmation(await api('/requirements/extract',{goal:body.goal}),finish);
});});
async function submitScenario(persist) {
  const body=scenarioInput();
  const finish=async authority=>{if(authority){body.constraints=authority.constraints;body.confirmation_id=authority.id;}
    const result=await api(`/projects/${project.id}/${persist?'revisions':'scenarios'}`,body);
    if(persist){showProject(result);await loadProjects();}else{scenario=result;$('#scenario-result').innerHTML=scenarioHTML(result);}};
  if(body.provider==='demo') await finish(null);
  else presentConfirmation(await api(`/projects/${project.id}/requirements/extract`,body),finish);
}
$('#new-project').addEventListener('click',()=>{$('#create-view').hidden=false;$('#project-view').hidden=true;$('#heading').textContent='Turn ambition into a plan.';providerInfo();$('#goal').focus();});
document.addEventListener('click',ev=>{
  const navigation=ev.target.closest('[data-view]'); if(navigation){view=navigation.dataset.view;if(project){$('#create-view').hidden=true;$('#project-view').hidden=false;render();}return;}
  const link=ev.target.closest('[data-project]'); if(link){action(async()=>showProject(await api('/projects/'+link.dataset.project)));return;}
  if(ev.target.id==='load-failures') action(async()=>{const failures=await api(`/projects/${project.id}/failures`);$('#failed-executions').innerHTML=failures.length?failures.map(f=>`<article class="risk"><h3>Failed attempt · ${e(new Date(f.created_at).toLocaleString())}</h3><p>${e(f.error_code.replaceAll('_',' '))}. No revision was saved.</p>${(f.invocations||[]).filter(i=>i.status==='error').map(i=>`<p><strong>${e(i.provider)} · ${e(i.role)}:</strong> ${e(i.error||'Request failed')}</p>`).join('')}${technicalDetails(f)}</article>`).join(''):'<p>No failed revisions recorded for this project.</p>';});
  if(ev.target.id==='commit-scenario' && $('#scenario-form').reportValidity()) action(async()=>{await submitScenario(true);});
});
document.addEventListener('change',ev=>{if(ev.target.id==='revision-select'){revisionIndex=+ev.target.value;render();}});
document.addEventListener('submit',ev=>{
  if(ev.target.id==='scenario-form'){ev.preventDefault();action(async()=>{await submitScenario(false);});}
  if(ev.target.id==='document-form'){ev.preventDefault();action(async()=>{const file=$('#document-file').files[0];if(file.size>400000)throw new Error('File too large. Maximum 100,000 UTF-8 characters.');if(!/\.(txt|md)$/i.test(file.name))throw new Error('Only .txt and .md files are supported.');const text=await file.text();const result=await api(`/projects/${project.id}/documents`,{name:file.name,text});$('#document-status').textContent=`Indexed ${result.chunks} chunks with ${result.embedding}.`;});}
  if(ev.target.id==='search-form'){ev.preventDefault();action(async()=>{const result=await api(`/projects/${project.id}/search`,{query:$('#query').value});$('#search-result').innerHTML=sourcesHTML(result.matches);});}
});
function providerInfo() {
  const name=$('#provider').value;
  $('#demo-constraints').hidden=name!=='demo';
  $('#live-constraints-hint').hidden=name==='demo';
  $('#demo-constraints').querySelectorAll('input').forEach(input=>{input.disabled=name!=='demo';input.required=name==='demo';});
  if(!project || !$('#create-view').hidden) $('#mode').textContent=name==='demo'?'NO-COST DEMO':'LIVE AI · CONFIRM REQUIREMENTS';
  if(name==='demo') {$('#provider-info').textContent='Offline Demo makes no external model calls.';return;}
  const providers=providerSettings?.providers||[];
  const selected=name==='multi'?Object.entries(providerSettings?.roles||{}).map(([role,p])=>({role,...providers.find(item=>item.provider===p)})):providers.filter(p=>p.provider===name);
  $('#provider-info').textContent=selected.map(p=>`${p.role?p.role+': ':''}${p.provider||'none'} / ${p.model||'not configured'} — ${p.ready?'configured; free quota may limit requests':p.message||'disabled'}`).join(' · ');
}
$('#provider').addEventListener('change',providerInfo);
action(async()=>{providerSettings=await api('/providers');providerInfo();await loadProjects();const saved=localStorage.getItem('northstar-project');if(saved){try{showProject(await api('/projects/'+saved));}catch{localStorage.removeItem('northstar-project');}}});
