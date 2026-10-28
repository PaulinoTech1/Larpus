// Exercise the actual chat submit handler with a delayed byte stream.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(events){
 const elements={};
 const element=id=>elements[id]??={value:'',disabled:false,textContent:'',children:[],dataset:{},append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},querySelector(){return null;},addEventListener(){},focus(){},getContext(){return {};}};
 // HTMLCollection exposes indexed items, but has no Array.at method.
 Object.defineProperty(element('messages').children,'at',{value:undefined});
 Object.defineProperty(element('messages'),'lastElementChild',{get(){return this.children[this.children.length-1]||null;}});
 const speech=[];let finish;
 const gate=new Promise(resolve=>finish=resolve),frames=events.map(e=>Buffer.from(JSON.stringify(e)+'\n'));
 let index=0,cancelled=false,generations=0;
 const sandbox={document:{getElementById:element,createElement:()=>element(Symbol()),createTextNode:text=>({textContent:text}),querySelector:()=>element('header'),querySelectorAll:()=>[]},window:{larpusVoice:{beginReply(){},enqueueSpeech:t=>speech.push(t),finishReply:t=>speech.push(['done',t]),stopPlayback:()=>speech.push('stop')}},matchMedia:()=>({matches:false}),requestAnimationFrame(){},setInterval(){},TextDecoder,Uint8Array,Option:function(text,value){this.text=text;this.value=value;},location:{replace(){}},devicePixelRatio:1,AbortController:typeof AbortController==='function'?AbortController:undefined,fetch:async (path,options)=>{
  if(path==='/api/chat/stream'){generations++;return {ok:true,status:200,body:{getReader(){return {async read(){if(index===1)await gate;if(options?.signal?.aborted){const error=Error('Stopped');error.name='AbortError';throw error;}return index<frames.length?{value:frames[index++],done:false}:{done:true};},async cancel(){cancelled=true;},releaseLock(){}};}}};}
  return {ok:true,json:async()=>path==='/api/personas'?{personas:[{id:'home-assistant',name:'Home',model:'local',skills:[]}]}:path==='/api/health'?{ollama:'online',models:['local']}:{status:'pass',checks:[]}};
 }};
 vm.createContext(sandbox);vm.runInContext(fs.readFileSync('web/app.js','utf8'),sandbox);
 return {sandbox,element,speech,finish,get cancelled(){return cancelled;},get generations(){return generations;}};
}
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 const app=setup([{type:'text',content:'First checked sentence. '},{type:'text',content:'Second sentence.'},{type:'done',sources:[{id:'ubuntu-26-04',title:'Ubuntu 26.04',url:'https://documentation.ubuntu.com/release-notes/26.04/',snapshot:'2026-10-09',locator:'document'}]}]);await tick();
 app.element('prompt').value='Hello';const submitted=app.element('chat').onsubmit({preventDefault(){}});await tick();
 assert.equal(app.speech[0],'First checked sentence. ','speech begins before stream completion');
 assert.equal(app.element('messages').lastElementChild.children[1].textContent,'First checked sentence. ');
 assert.equal(vm.runInContext('history.length',app.sandbox),0,'incomplete response is not conversation history');
 app.finish();await submitted;
 assert.equal(vm.runInContext('history.at(-1).content',app.sandbox),'First checked sentence. Second sentence.');
 assert.equal(app.element('messages').lastElementChild.children[2].disabled,false);
 assert.match(app.element('messages').lastElementChild.children[3].textContent,/LOCAL REFERENCES/);
 assert.equal(app.speech.at(-1)[1],'First checked sentence. Second sentence.','reference metadata must not enter spoken reply');
 assert.equal(app.speech.includes('stop'),false,'successful completion must not cancel speech');
 assert.equal(app.cancelled,true);
 const held=setup([{type:'text',content:'Checked partial sentence. '},{type:'error',error:'Output held.'}]);await tick();held.element('prompt').value='Hello';
 const failed=held.element('chat').onsubmit({preventDefault(){}});await tick();held.finish();await failed;
 assert.equal(vm.runInContext('history.length',held.sandbox),0);
 assert.equal(held.speech.at(-1),'stop');assert.match(held.element('messages').lastElementChild.children[0].textContent,/INCOMPLETE/);
 assert.equal(held.element('prompt').value,'Hello');assert.equal(held.element('notice').textContent,'Output held.');
 const truncated=setup([{type:'text',content:'Partial sentence. '}]);await tick();truncated.element('prompt').value='Hello';
 const stopped=truncated.element('chat').onsubmit({preventDefault(){}});await tick();truncated.finish();await stopped;
 assert.equal(vm.runInContext('history.length',truncated.sandbox),0);assert.match(truncated.element('notice').textContent,/ended early/);
 assert.equal(truncated.generations,1,'truncation must not automatically replay generation');
 const interrupted=setup([{type:'text',content:'A sentence. '},{type:'done'}]);await tick();interrupted.element('prompt').value='Hello';
 const aborting=interrupted.element('chat').onsubmit({preventDefault(){}});await tick();interrupted.sandbox.window.larpusCancelGeneration();interrupted.finish();await aborting;
 assert.equal(interrupted.speech.filter(x=>x==='stop').length,1,'abort cleanup must not clear the next microphone capture');
 assert.equal(vm.runInContext('history.length',interrupted.sandbox),0);assert.match(interrupted.element('notice').textContent,/Stopped/);
 const broker=setup([{type:'text',content:'Checked partial sentence. '},{type:'error',code:'cancellation_unconfirmed',error:'Generic broker refusal.'}]);await tick();broker.element('prompt').value='Hello';
 const refused=broker.element('chat').onsubmit({preventDefault(){}});await tick();broker.finish();await refused;
 assert.match(broker.element('notice').textContent,/broker: cancellation_unconfirmed/);
 assert.match(broker.element('notice').textContent,/repeated retries may not recover/);
 assert.equal(vm.runInContext('history.length',broker.sandbox),0,'broker refusal must not save partial output');
 assert.equal(broker.speech.at(-1),'stop');assert.equal(broker.generations,1,'broker refusals must not automatically replay generation');
 console.log('Chat UI: incremental text/speech, successful history, held/truncated streams passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
