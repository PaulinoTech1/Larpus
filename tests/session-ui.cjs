const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {bindSession}=require('../web/session.js');
const html=fs.readFileSync('web/index.html','utf8');
for(const id of ['session-panel','session-login','session-password','session-unlock','session-error'])assert.ok(html.includes('id="'+id+'"'),'Missing reauthentication element: '+id);
assert.ok(html.includes('/session.js')&&html.indexOf('/session.js')<html.indexOf('/app.js'),'Session binding must load before the application');
function elements(){const values={};return id=>values[id]??={value:'',disabled:false,hidden:true,textContent:'',children:[],dataset:{},append(...n){this.children.push(...n);},replaceChildren(...n){this.children=n;},querySelector(){return null;},addEventListener(){},focus(){this.focused=true;},getContext(){return {};}};}
(async()=>{
 const el=elements();let expired=0,restored=0,status=401,calls=[];
 const auth=bindSession({element:el,fetch:async(path,options)=>{calls.push(path);return {ok:status===200,status,json:async()=>({error:'denied'})};},onExpired:()=>expired++,onRestored:()=>restored++});
 assert.throws(()=>auth.check({status:401}),/conversation.*retained/i);assert.equal(auth.locked,true);assert.equal(el('session-panel').hidden,false);
 assert.throws(()=>auth.check({status:401}),/retained/i);assert.equal(expired,1,'polling does not repeatedly steal focus');
 el('session-password').value='wrong';await el('session-login').onsubmit({preventDefault(){}});assert.equal(auth.locked,true);assert.equal(el('session-password').value,'');assert.match(el('session-error').textContent,/Larping/);
 status=200;el('session-password').value='correct';await el('session-login').onsubmit({preventDefault(){}});assert.equal(auth.locked,false);assert.equal(restored,1);assert.equal(el('session-panel').hidden,true);assert.deepEqual(calls,['/api/login','/api/login']);
 const element=elements();let invalid=false,chatCalls=0,navigations=0;
 const sandbox={document:{getElementById:element,createElement:()=>element(Symbol()),createTextNode:t=>({textContent:t}),querySelector:()=>element('header'),querySelectorAll:()=>[]},window:{bindLarpusSession:bindSession},matchMedia:()=>({matches:false}),requestAnimationFrame(){},setInterval(){},TextDecoder,Uint8Array,Option:function(t,v){this.text=t;this.value=v;},location:{replace(){navigations++;}},devicePixelRatio:1,AbortController,fetch:async(path)=>{
  if(path==='/api/login'){invalid=false;return {status:200,ok:true,json:async()=>({ok:true})};}
  if(path==='/api/chat/stream')chatCalls++;
  if(invalid)return {status:401,ok:false,json:async()=>({error:'Password required'})};
  return {status:200,ok:true,json:async()=>path==='/api/personas'?{personas:[{id:'home-assistant',name:'Home',model:'local',skills:[]}],skills:[]}:path==='/api/health'?{ollama:'online',models:['local']}:{status:'pass',checks:[]}};
 }};
 vm.createContext(sandbox);vm.runInContext(fs.readFileSync('web/app.js','utf8'),sandbox);await new Promise(r=>setImmediate(r));
 vm.runInContext("history=[{role:'user',content:'Prior question'},{role:'assistant',content:'Prior answer'}];conversation={record:{summary:'retained'},through:2,needs:()=>false,wire:(h,q)=>[...h,{role:'user',content:q}]};",sandbox);
 element('prompt').value='Unsent draft';invalid=true;await vm.runInContext("api('/api/station-health').catch(()=>{})",sandbox);
 assert.equal(navigations,0);assert.equal(vm.runInContext('history.length',sandbox),2);assert.equal(vm.runInContext('conversation.record.summary',sandbox),'retained');assert.equal(element('prompt').value,'Unsent draft');assert.equal(element('send').disabled,true);
 element('connection').textContent='GATEWAY UNAVAILABLE';element('session-password').value='correct';await element('session-login').onsubmit({preventDefault(){}});assert.equal(chatCalls,0,'reauthentication must not replay a failed action');assert.equal(navigations,0);await new Promise(r=>setImmediate(r));assert.match(element('connection').textContent,/ONLINE/);
 invalid=true;await element('chat').onsubmit({preventDefault(){}});assert.equal(chatCalls,1);assert.equal(vm.runInContext('history.length',sandbox),2);assert.equal(element('prompt').value,'Unsent draft');assert.equal(vm.runInContext('conversation.record.summary',sandbox),'retained');assert.equal(navigations,0);
 console.log('Session UI: in-page reauthentication, preserved transcript/draft/record, cleared password and no automatic replay passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
