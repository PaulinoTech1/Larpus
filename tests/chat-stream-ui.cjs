// Exercise the actual chat submit handler with a delayed byte stream.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(events){
 const elements={};
 const element=id=>elements[id]??={value:'',disabled:false,textContent:'',children:[],dataset:{},append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},querySelector(){return null;},addEventListener(){},focus(){},getContext(){return {};}};
 const speech=[];let finish;
 const gate=new Promise(resolve=>finish=resolve),frames=events.map(e=>Buffer.from(JSON.stringify(e)+'\n'));
 let index=0,cancelled=false;const fetches=[];
 const sandbox={document:{getElementById:element,createElement:()=>element(Symbol()),createTextNode:text=>({textContent:text}),querySelector:()=>element('header'),querySelectorAll:()=>[]},window:{larpusVoice:{beginReply(){},enqueueSpeech:t=>speech.push(t),finishReply:t=>speech.push(['done',t]),stopPlayback:()=>speech.push('stop')}},matchMedia:()=>({matches:false}),requestAnimationFrame(){},setInterval(){},TextDecoder,Uint8Array,Option:function(text,value){this.text=text;this.value=value;},location:{replace(){}},devicePixelRatio:1,AbortController:typeof AbortController==='function'?AbortController:undefined,fetch:async (path,options)=>{fetches.push({path,options});
  if(path==='/api/voice')return {ok:false,status:429,headers:{get:name=>name==='Retry-After'?'7':null},json:async()=>({error:'Too many requests. Try again shortly.'})};

  if(path==='/api/chat/stream')return {ok:true,status:200,body:{getReader(){return {async read(){if(index===1)await gate;if(options?.signal?.aborted){const error=Error('Stopped');error.name='AbortError';throw error;}return index<frames.length?{value:frames[index++],done:false}:{done:true};},async cancel(){cancelled=true;},releaseLock(){}};}}};
  return {ok:true,json:async()=>path==='/api/personas'?{personas:[{id:'home-assistant',name:'Home',model:'local',skills:[]}]}:path==='/api/health'?{ollama:'online',models:['local']}:{status:'pass',checks:[]}};
 }};
 vm.createContext(sandbox);vm.runInContext(fs.readFileSync('web/app.js','utf8'),sandbox);
 return {sandbox,element,speech,finish,fetches,get cancelled(){return cancelled;}};
}
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{
 const app=setup([{type:'text',content:'First checked sentence. '},{type:'text',content:'Second sentence.'},{type:'done',sources:[{id:'ubuntu-26-04',title:'Ubuntu 26.04',url:'https://documentation.ubuntu.com/release-notes/26.04/',snapshot:'2026-10-09',locator:'document'}]}]);await tick();
 app.element('prompt').value='Hello';const submitted=app.element('chat').onsubmit({preventDefault(){}});await tick();
 assert.equal(app.speech[0],'First checked sentence. ','speech begins before stream completion');
 assert.equal(app.element('messages').children.at(-1).children[1].textContent,'First checked sentence. ');
 assert.equal(vm.runInContext('history.length',app.sandbox),0,'incomplete response is not conversation history');
 // Speech requests must not share the chat stream's AbortController.
 const speechCall=vm.runInContext("api('/api/voice',{action:'synthesize',text:'x'},{abortable:false})",app.sandbox).catch(e=>e);
 const chatScoped=vm.runInContext("api('/api/voice',{action:'synthesize',text:'y'})",app.sandbox).catch(e=>e);
 const [speechError]=await Promise.all([speechCall,chatScoped]);
 const voiceFetches=app.fetches.filter(f=>f.path==='/api/voice');
 assert.equal(voiceFetches[0].options.signal,undefined,'speech synthesis is not abortable by STOP GENERATION');
 if(typeof AbortController==='function')assert.ok(voiceFetches[1].options.signal,'default api calls keep the chat signal');
 assert.equal(speechError.status,429);assert.equal(speechError.retryAfter,7,'Retry-After is exposed to the speech queue');
 app.finish();await submitted;
 assert.equal(vm.runInContext('history.at(-1).content',app.sandbox),'First checked sentence. Second sentence.');
 assert.equal(app.element('messages').children.at(-1).children[2].disabled,false);
 assert.match(app.element('messages').children.at(-1).children[3].textContent,/LOCAL REFERENCES/);
 assert.equal(app.speech.at(-1)[1],'First checked sentence. Second sentence.','reference metadata must not enter spoken reply');
 assert.equal(app.cancelled,true);
 const held=setup([{type:'text',content:'Checked partial sentence. '},{type:'error',error:'Output held.'}]);await tick();held.element('prompt').value='Hello';
 const failed=held.element('chat').onsubmit({preventDefault(){}});await tick();held.finish();await failed;
 assert.equal(vm.runInContext('history.length',held.sandbox),0);
 assert.deepEqual(held.speech.slice(-2),['stop',['done','Checked partial sentence. ']],'a partial reply updates the replay target after stopping speech');
 assert.equal(held.element('messages').children.at(-1).children[2].disabled,false,'partial reply keeps REPLAY REPLY enabled');
 assert.match(held.element('messages').children.at(-1).children[0].textContent,/INCOMPLETE/);
 assert.equal(held.element('prompt').value,'Hello');assert.equal(held.element('notice').textContent,'Output held.');
 const truncated=setup([{type:'text',content:'Partial sentence. '}]);await tick();truncated.element('prompt').value='Hello';
 const stopped=truncated.element('chat').onsubmit({preventDefault(){}});await tick();truncated.finish();await stopped;
 assert.equal(vm.runInContext('history.length',truncated.sandbox),0);assert.match(truncated.element('notice').textContent,/ended early/);
 const interrupted=setup([{type:'text',content:'A sentence. '},{type:'done'}]);await tick();interrupted.element('prompt').value='Hello';
 const aborting=interrupted.element('chat').onsubmit({preventDefault(){}});await tick();interrupted.sandbox.window.larpusCancelGeneration();interrupted.finish();await aborting;
 assert.equal(interrupted.speech.filter(x=>x==='stop').length,1,'abort cleanup must not clear the next microphone capture');
 assert.equal(vm.runInContext('history.length',interrupted.sandbox),0);assert.match(interrupted.element('notice').textContent,/Stopped/);
 console.log('Chat UI: incremental text/speech, successful history, held/truncated streams, partial replay and speech abort isolation passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
