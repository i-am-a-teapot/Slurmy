'use strict';
if(document.body.dataset.page==='job'&&document.querySelector('#job-batches')){
 const panel=$('#job-batches'),list=$('#batch-list'),pagination=$('#batch-pagination');
 const jobId=document.body.dataset.job,expanded=new Map();let batchPage=0,listRequest=0,retryTimer=null;
 const url=suffix=>`/api/jobs/${encodeURIComponent(jobId)}/batches${suffix}`;
 function freshness(data){const info=data.refresh||{},when=info.updated?new Date(info.updated*1000).toLocaleTimeString():'unknown time';return info.stale?`Saved snapshot from ${when} · may be out of date${info.refreshing?' · refreshing in background':''}`:`Last refreshed ${when}`;}
 function pager(container,current,total,size,change,label){
  const pages=Math.max(1,Math.ceil(total/size));container.replaceChildren();
  const previous=button('Previous',()=>change(current-1)),next=button('Next',()=>change(current+1));
  previous.disabled=current===0;next.disabled=current+1>=pages;
  const jump=el('label',undefined,'page-jump'),input=el('input');input.type='number';input.min=1;input.max=pages;input.value=current+1;input.setAttribute('aria-label',label);
  input.addEventListener('change',()=>{const value=Number(input.value);if(Number.isInteger(value)&&value>=1&&value<=pages)change(value-1);else input.value=current+1;});
  jump.append(document.createTextNode('Page '),input,document.createTextNode(` of ${pages}`));container.append(previous,jump,next);
 }
 async function loadPairs(details,content,batch,pageNumber=0){
  expanded.set(batch.id,pageNumber);const request=String(Number(content.dataset.request||0)+1);content.dataset.request=request;
  if(!content.childNodes.length)content.append(el('p','Loading solver-problem pairs…','muted'));
  try{
   const data=await api(url(`/${batch.id}?`)+params({page:pageNumber,per_page:50}));
   if(!details.isConnected||!details.open||content.dataset.request!==request)return;
   const last=Math.max(0,Math.ceil(data.total/50)-1);if(pageNumber>last){loadPairs(details,content,batch,last);return;}
   const table=el('table'),head=el('thead'),body=el('tbody'),scroll=el('div',undefined,'table-scroll');
   const headings=el('tr');for(const name of ['Order','Pair ID','Solver','Problem','Status','Output'])headings.append(el('th',name));head.append(headings);table.append(head,body);scroll.append(table);
   for(const task of data.tasks){
    const problem=link(task.problem.split('/').pop()||'—',`/jobs/${encodeURIComponent(jobId)}/problems/${task.id}?`+params({}));problem.title=task.problem;
    const solver=el('span',task.solver||'—');solver.title=task.command;
    const inspect=task.output?button('Inspect output',()=>openOutput(task)):(task.diagnostic||task.diagnostic_available)?button('Inspect log',()=>openDiagnostic(task)):'—';
    body.append(tableRow([String(task.position),String(task.id),solver,problem,taskStatus(task),inspect]));
   }
   if(!data.tasks.length)body.append(tableRow(['No solver-problem pairs in this batch.','','','','','']));
   const controls=el('div',undefined,'pagination');pager(controls,pageNumber,data.total,50,page=>loadPairs(details,content,batch,page),`Go to pair page in batch ${batch.id}`);
   content.replaceChildren(el('p',freshness(data),'muted'),scroll,controls);
  }catch(error){if(content.dataset.request!==request||!details.isConnected)return;content.replaceChildren(el('p',error.message,'error'),button('Retry',()=>loadPairs(details,content,batch,pageNumber)));}
 }
 async function loadList(){
  clearTimeout(retryTimer);retryTimer=null;
  if(!panel.open)return;const request=++listRequest;
  if(!list.childNodes.length)list.append(el('p','Loading batches…','muted'));
  try{
   const data=await api(url('?')+params({page:batchPage,per_page:25}));if(request!==listRequest||!panel.open)return;
   const last=Math.max(0,Math.ceil(data.total/25)-1);if(batchPage>last){batchPage=last;loadList();return;}
   text('#batch-freshness',`${data.total} batch${data.total===1?'':'es'} · ${freshness(data)}`);$('#batch-warning').hidden=!data.membership_estimated;
   const children=[];
   for(const batch of data.batches){
    const details=el('details',undefined,'batch-inspector'),summary=el('summary'),content=el('div');
    const title=el('span',`Batch ${batch.id}`),progress=el('span',`${batch.finished} / ${batch.total} finished${batch.state==='Finished'?'':' · '+batch.state}`,'muted');summary.append(title,progress);
    const names=el('p',batch.solvers.join(' · ')||'Solver configurations unavailable','muted');
    if(batch.slurm_id)names.append(document.createTextNode(` · SLURM ${batch.slurm_id}${batch.node?' · '+batch.node:''}`));
    details.append(summary,names,content);details.addEventListener('toggle',()=>{if(details.open)loadPairs(details,content,batch,expanded.get(batch.id)||0);else expanded.delete(batch.id);});
    if(expanded.has(batch.id))details.open=true;children.push(details);
   }
   if(!children.length)children.push(el('p',data.refresh?.refreshing?'The batch plan is loading. It will appear when the job refresh completes.':'No batch plan is available for this job.','muted'));
   list.replaceChildren(...children);pager(pagination,batchPage,data.total,25,page=>{expanded.clear();batchPage=page;loadList();},'Go to batches page');
   if(data.refresh?.refreshing)retryTimer=setTimeout(loadList,1000);
  }catch(error){if(request!==listRequest)return;text('#batch-freshness',`Could not update batches: ${error.message}`);if(!list.querySelector('details'))list.replaceChildren(button('Retry',loadList));}
 }
 panel.addEventListener('toggle',()=>{if(panel.open)loadList();else{++listRequest;clearTimeout(retryTimer);retryTimer=null;}});
 window.SlurmyBatches={refresh:loadList};
}
