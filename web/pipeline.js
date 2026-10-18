(()=>{
function bindPipeline({api,element,isBusy,option=(name,id)=>new Option(name,id)}){
 let state=null,pending=false;const select=element('pipeline-select'),button=element('switch-pipeline'),status=element('retrieval-pipeline-status');
 function controls(){
  select.disabled=pending||!state||isBusy();
  button.disabled=select.disabled||select.value===state?.active_id||!state?.pipelines.find(p=>p.id===select.value)?.available;
 }
 function render(value){
  state=value;const chosen=select.value;
  select.replaceChildren(...value.pipelines.map(p=>{const o=option(p.name,p.id);o.disabled=!p.available;return o;}));
  select.value=value.pipelines.some(p=>p.id===chosen&&p.available)?chosen:value.active_id;
  const active=value.pipelines.find(p=>p.id===value.active_id);
  const safety=value.active_id==='assembly'&&value.last_used==='numpy'?' — last query used NumPy safety check':'';
  status.textContent=`Active: ${active?.name||value.active_id}${safety}${value.notice?' — '+value.notice:''}`;controls();
 }
 async function refresh(){if(pending)return;try{render(await api('/api/retrieval-pipeline'));}catch(e){state=null;status.textContent=e.message;controls();}}
 select.onchange=controls;
 button.onclick=async()=>{
  controls();if(button.disabled)return;pending=true;controls();
  try{render(await api('/api/retrieval-pipeline',{pipeline_id:select.value}));}
  catch(e){state=null;status.textContent=e.message;}
  finally{pending=false;controls();}
 };
 return {refresh,controls};
}
if(typeof window!=='undefined')window.bindLarpusPipeline=bindPipeline;
if(typeof module!=='undefined')module.exports={bindPipeline};
})();
