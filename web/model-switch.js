(()=>{
const WARNING='Switching models pauses chat while the current work finishes and the new model loads. This can take a few minutes, especially after a cold start. Voice remains available. Your conversation stays here.';
const labels={ready:'Ready',waiting:'Waiting for current reply',unloading:'Unloading current model',loading:'Loading selected model',verifying:'Checking model',restoring:'Restoring previous model',failed:'Model switch failed'};
function bindModelSwitch({api,element,isBusy,onState,option=(name,id)=>new Option(name,id)}){
 let state=null,pending=false;const select=element('model-select'),button=element('switch-model'),status=element('model-switch-status');
 element('model-switch-warning').textContent=WARNING;
 function controls(){button.disabled=pending||!state||state.phase!=='ready'||isBusy()||select.value===state.active_id||!state.models?.find(m=>m.id===select.value)?.available;select.disabled=pending||!state||state.phase!=='ready'||isBusy();}
 function render(value){
  state=value;const models=value.models||[],chosen=select.value;select.replaceChildren(...models.map(m=>{const o=option(m.name,m.id);o.disabled=!m.available;return o;}));
  select.value=value.target_id||(models.some(m=>m.id===chosen)?chosen:value.active_id);
  const active=models.find(m=>m.id===value.active_id);element('model-current').textContent=active?.name||value.active_id;
  status.textContent=(labels[value.phase]||'Checking model')+(value.error?': '+value.error:'');controls();onState(value);
 }
 async function refresh(){try{render(await api('/api/model-selection'));}catch(e){state=null;status.textContent=e.message;controls();}}
 select.onchange=controls;
 button.onclick=async()=>{
  controls();if(button.disabled)return;pending=true;controls();
  try{const response=await api('/api/model-selection',{model_id:select.value});render({...state,...response,models:response.models||state.models});}catch(e){status.textContent=e.message;}finally{pending=false;controls();}
 };
 return {refresh,controls};
}
if(typeof window!=='undefined')window.bindLarpusModelSwitch=bindModelSwitch;
if(typeof module!=='undefined')module.exports={bindModelSwitch,WARNING};
})();
