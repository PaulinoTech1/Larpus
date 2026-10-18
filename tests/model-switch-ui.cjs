const assert=require('node:assert/strict');
const {bindModelSwitch,WARNING}=require('../web/model-switch.js');
(async()=>{
 const elements={};const el=id=>elements[id]??={value:'',disabled:false,textContent:'',replaceChildren(...v){this.options=v;}};
 let state={active_id:'larpus-3.5',target_id:null,phase:'ready',models:[{id:'larpus-3.5',name:'Larpus 3.5 27B Q4',tag:'qwen3.5:27b-q4_K_M',available:true},{id:'larpus-3.8',name:'Larpus 3.8 27B Q4',tag:'larpus3.8:27b-q4',available:true}]},calls=[],observed;
 const api=async(path,body)=>{calls.push(body);return body?{...state,phase:'loading',target_id:body.model_id}:state;};
 const c=bindModelSwitch({api,element:el,isBusy:()=>false,onState:s=>observed=s,option:(name,id)=>({text:name,value:id})});await c.refresh();
 assert.equal(el('model-switch-warning').textContent,WARNING);el('model-select').value='larpus-3.8';el('model-select').onchange();assert.equal(calls.filter(Boolean).length,0);assert.equal(el('switch-model').disabled,false);
 await el('switch-model').onclick();assert.equal(calls.filter(Boolean).length,1);assert.equal(observed.phase,'loading');assert.equal(el('switch-model').disabled,true);assert.match(el('model-switch-status').textContent,/Loading/);
 state={...state,active_id:'larpus-3.8',phase:'ready'};await c.refresh();assert.equal(observed.active_id,'larpus-3.8');assert.match(el('model-current').textContent,/3.8/);
 state={...state,phase:'failed',error:'Recovery failed'};await c.refresh();assert.equal(el('switch-model').disabled,true);assert.match(el('model-switch-status').textContent,/Recovery failed/);
 console.log('Model switch UI: explicit action, warning, busy state, reload status and failure passed.');
})();
