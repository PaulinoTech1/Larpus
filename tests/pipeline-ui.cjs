const assert=require('node:assert/strict');
const {bindPipeline}=require('../web/pipeline.js');
(async()=>{
 const els={};const element=id=>els[id]??={value:'',disabled:false,textContent:'',replaceChildren(...v){this.options=v;}};
 let busy=false,calls=[],state={active_id:'assembly',requested_id:'assembly',notice:null,pipelines:[{id:'assembly',name:'Assembly pipeline',available:true},{id:'numpy',name:'NumPy',available:true}]};
 const c=bindPipeline({element,isBusy:()=>busy,option:(name,id)=>({text:name,value:id}),api:async(path,body)=>{if(body){calls.push(body);state={...state,active_id:body.pipeline_id,requested_id:body.pipeline_id};}return state;}});
 await c.refresh();assert.match(element('retrieval-pipeline-status').textContent,/Assembly pipeline/);
 element('pipeline-select').value='numpy';element('pipeline-select').onchange();assert.equal(calls.length,0);
 await element('switch-pipeline').onclick();assert.deepEqual(calls,[{pipeline_id:'numpy'}]);assert.match(element('retrieval-pipeline-status').textContent,/NumPy/);
 busy=true;c.controls();assert.equal(element('switch-pipeline').disabled,true);
 busy=false;state={...state,active_id:'numpy',requested_id:'assembly',notice:'Assembly failed; using NumPy.',pipelines:[{id:'assembly',name:'Assembly pipeline',available:false},{id:'numpy',name:'NumPy',available:true}]};
 await c.refresh();assert.match(element('retrieval-pipeline-status').textContent,/Assembly failed/);assert.equal(element('pipeline-select').options[0].disabled,true);
 console.log('Pipeline UI: explicit switching, actual status, busy controls, fallback passed.');
})();
