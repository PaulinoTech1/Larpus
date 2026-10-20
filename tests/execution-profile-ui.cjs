// Exercise the actual chat submit handler with a delayed byte stream.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(events){
 const elements={};
 const element=id=>elements[id]??={value:'',disabled:false,textContent:'',children:[],dataset:{},append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},querySelector(){return null;},addEventListener(){},focus(){},getContext(){return {};}};
 const speech=[];let finish;
 const gate=new Promise(resolve=>finish=resolve),frames=events.map(e=>Buffer.from(JSON.stringify(e)+'\n'));
 let index=0,cancelled=false;
 const sandbox={document:{getElementById:element,createElement:()=>element(Symbol()),createTextNode:text=>({textContent:text}),querySelector:()=>element('header'),querySelectorAll:()=>[]},window:{larpusVoice:{beginReply(){},enqueueSpeech:t=>speech.push(t),finishReply:t=>speech.push(['done',t]),stopPlayback:()=>speech.push('stop')}},matchMedia:()=>({matches:false}),requestAnimationFrame(){},setInterval(){},TextDecoder,Uint8Array,Option:function(text,value){this.text=text;this.value=value;},location:{replace(){}},devicePixelRatio:1,AbortController:typeof AbortController==='function'?AbortController:undefined,fetch:async (path,options)=>{
  if(path==='/api/chat/stream')return {ok:true,status:200,body:{getReader(){return {async read(){if(index===1)await gate;if(options?.signal?.aborted){const error=Error('Stopped');error.name='AbortError';throw error;}return index<frames.length?{value:frames[index++],done:false}:{done:true};},async cancel(){cancelled=true;},releaseLock(){}};}}};
  return {ok:true,json:async()=>path==='/api/personas'?{personas:[{id:'home-assistant',name:'Home',model:'local',skills:[]}]}:path==='/api/health'?{ollama:'online',models:['local']}:{status:'pass',checks:[]}};
 }};
 vm.createContext(sandbox);vm.runInContext(fs.readFileSync('web/app.js','utf8'),sandbox);
 return {sandbox,element,speech,finish,get cancelled(){return cancelled;}};
}

const app=setup([]);
assert.deepEqual(JSON.parse(JSON.stringify(vm.runInContext('executionRequest()',app.sandbox))),{});
app.element('execution-profile').value='ultra-fast';app.element('execution-interaction').value='coding';
assert.deepEqual(JSON.parse(JSON.stringify(vm.runInContext('executionRequest()',app.sandbox))),{execution:{profile:'ultra-fast',interaction:'coding'}});
app.element('execution-profile').value='diagnostic';app.element('execution-base').value='ultra-fast';
assert.equal(vm.runInContext('executionRequest().execution.base',app.sandbox),'ultra-fast');
assert.match(fs.readFileSync('web/index.html','utf8'),/Ultra Fast.*security enforced/);
app.sandbox.performance={now:()=>150};
vm.runInContext("recordFirstRender(document.getElementById('probe'),100)",app.sandbox);
assert.equal(app.element('probe').dataset.firstDomUpdateMs,'50.000');
app.sandbox.performance={now:()=>250};
vm.runInContext("recordFirstRender(document.getElementById('probe'),100)",app.sandbox);
assert.equal(app.element('probe').dataset.firstDomUpdateMs,'50.000');
console.log('Execution controls: defaults, independent interaction and Diagnostic base passed.');
