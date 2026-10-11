const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const code=fs.readFileSync('web/teaching.js','utf8');
function fixture(initial=null){
  let raw=initial,fail=false;
  const storage={getItem:()=>raw,setItem:(k,v)=>{if(fail)throw Error('quota');raw=v;},removeItem:()=>{raw=null;}};
  const window={};vm.runInNewContext(code,{window,Date,JSON,Set,Error,Object,Number});
  return {Teaching:window.LarpusTeaching,store:new window.LarpusTeaching(storage),storage,get raw(){return raw;},set raw(v){raw=v;},set fail(v){fail=v;}};
}
const f=fixture(),T=f.Teaching,scope=T.scope('mathematician','linear-algebra'),settings={...T.defaults(),method:'worked-example'};
assert.equal(f.store.request(scope,'Question').question,'Question');assert.equal(f.raw,null);
assert.throws(()=>f.store.start(scope,T.defaults(),'why','success'));
f.store.start(scope,settings,'Try examples','Solve independently');
assert.throws(()=>f.store.start(scope,settings,'why','success'));
assert.throws(()=>f.store.review(scope,true,'Accept before trying'));
assert.throws(()=>f.store.feedback(scope,'helpful','Not yet'));
assert.equal(JSON.parse(f.store.request(scope,'Question').question.split('\n').slice(1).join('\n')).mode,'trial');
assert.equal(f.store.request(T.scope('mathematician'),'Other topic').question,'Other topic','no cross-skill preference leakage');
for(let i=0;i<3;i++)f.store.completed(f.store.request(scope,'Question').token);
assert.equal(f.store.trial(scope).replies,3);
assert.equal(f.store.request(scope,'Question').question,'Question','three-reply trial returns to baseline');
f.store.feedback(scope,'helpful','Fewer hints needed');f.store.review(scope,true,'Keep the example-first style');
assert.equal(f.store.profile(scope).versions.length,1);
assert.equal(JSON.parse(f.store.request(scope,'Question').question.split('\n').slice(1).join('\n')).mode,'accepted');
f.store.restore(scope,0,'Return to default');assert.equal(f.store.profile(scope).versions.length,2);
assert.equal(f.store.accepted(scope).method,'mixed');assert.equal(f.store.profile(scope).versions[0].settings.method,'worked-example');
const reload=new T(f.storage);assert.equal(reload.data.experiments[0].review,'Keep the example-first style');
assert.equal(reload.profile(scope).versions.length,2);
reload.start(scope,settings,'Retry','Apply unaided');assert.throws(()=>reload.restore(scope,0,'Cannot during trial'));
const cancelled=reload.request(scope,'Question').token;reload.review(scope,false,'Not useful now');
assert.throws(()=>reload.completed(cancelled));assert.equal(reload.accepted(scope).method,'mixed');
assert.throws(()=>reload.request(scope,'x'.repeat(8000))); // accepted metadata also stays bounded
assert.throws(()=>reload.start('bad scope',settings,'why','success'));
assert.throws(()=>reload.start(scope,{...settings,method:'<script>unsafe</script>'},'why','success'));
assert.throws(()=>reload.start(scope,settings,'','success'));
const rawBefore=f.raw;f.fail=true;assert.throws(()=>reload.start(scope,settings,'why','success'));assert.equal(f.raw,rawBefore);assert.equal(reload.trial(scope),undefined);f.fail=false;
const stale=new T(f.storage);reload.start(scope,settings,'Try again','Solve without hints');const changed=f.raw;
assert.throws(()=>stale.start(T.scope('statistician'),settings,'why','success'),/another tab/);assert.equal(f.raw,changed);
stale.request(scope,'Refresh');assert.equal(stale.trial(scope).rationale,'Try again');
const bad=fixture('broken');assert.ok(bad.store.error);assert.throws(()=>bad.store.start(scope,settings,'why','success'));assert.equal(bad.raw,'broken');
assert.equal(bad.store.request(scope,'Normal chat').question,'Normal chat');bad.store.reset();assert.equal(bad.raw,null);
const huge=fixture('x'.repeat(160001));assert.ok(huge.store.error);assert.equal(huge.raw.length,160001);
for(const mutate of [d=>d.profiles.push({scope,versions:[]}),d=>d.experiments[0].settings.method='unbounded',d=>d.experiments[0].feedback[0].rating='perfect',d=>d.experiments[0].replies=4,d=>d.extra=true]){
  const d=JSON.parse(changed);mutate(d);assert.throws(()=>T.valid(d));
}
const full=fixture();for(let i=0;i<80;i++){full.store.start(scope,settings,'why','success');full.store.review(scope,false,'Rejected');}
const fullBefore=full.raw;assert.throws(()=>full.store.start(scope,settings,'why','success'));assert.equal(full.raw,fullBefore,'journal overflow must preserve history');
const versions=fixture();for(let i=0;i<20;i++){versions.store.start(scope,{...T.defaults(),method:i%2?'socratic':'direct'},'why','success');versions.store.completed(versions.store.request(scope,'Question').token);versions.store.review(scope,true,'Reviewed');}
const versionsBefore=versions.raw;assert.throws(()=>versions.store.restore(scope,0,'Full version history'));assert.equal(versions.raw,versionsBefore);
const crowded=fixture();for(let i=0;i<24;i++){const k=T.scope('role-'+i);crowded.store.start(k,settings,'why','success');crowded.store.completed(crowded.store.request(k,'Question').token);crowded.store.review(k,true,'Reviewed');}
const extra=T.scope('role-extra');crowded.store.start(extra,settings,'why','success');crowded.store.completed(crowded.store.request(extra,'Question').token);
assert.throws(()=>crowded.store.review(extra,true,'Too many profiles'));assert.equal(crowded.store.trial(extra).status,'trial');
const notes=fixture();notes.store.start(scope,settings,'why','success');notes.store.completed(notes.store.request(scope,'Question').token);
for(let i=0;i<6;i++)notes.store.feedback(scope,'mixed','Observation');const notesBefore=notes.raw;assert.throws(()=>notes.store.feedback(scope,'mixed','Another'));assert.equal(notes.raw,notesBefore);

// Exercise the real UI bindings and real chat submit handler together.
async function integration(){
  const elements={},requests=[];let raw=null,failStream=false;
  const element=id=>elements[id]??={id,value:'',disabled:false,textContent:'',children:[],dataset:{},
    append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;this.value=nodes[0]?.value||'';},
    querySelector(){return null;},querySelectorAll(){return Object.values(elements).filter(e=>typeof e.id==='string'&&e.id.startsWith('teaching-'));},addEventListener(){},focus(){},getContext(){return {};}};
  const sandbox={window:{confirm:()=>true},localStorage:{getItem:()=>raw,setItem:(k,v)=>{raw=v;},removeItem:()=>{raw=null;}},
    document:{getElementById:element,createElement:()=>element(Symbol()),createTextNode:text=>({textContent:text}),querySelector:()=>element('header'),querySelectorAll:()=>[]},
    Date,JSON,Set,Error,Object,Number,TextDecoder,Uint8Array,matchMedia:()=>({matches:false}),requestAnimationFrame(){},setInterval(){},
    Option:function(text,value){this.text=text;this.value=value;},location:{replace(){}},devicePixelRatio:1,
    fetch:async(path,options)=>{
      if(path==='/api/chat/stream'){
        requests.push(JSON.parse(options.body));let done=false;
        return {ok:true,status:200,body:{getReader:()=>({read:async()=>{if(done)return {done:true};done=true;return {value:Buffer.from(JSON.stringify(failStream?{type:'error',error:'Held'}:{type:'text',content:'Try this example.'})+'\n'+(failStream?'':JSON.stringify({type:'done'})+'\n')),done:false};},cancel:async()=>{},releaseLock(){}})}};
      }
      return {ok:true,json:async()=>path==='/api/personas'?{personas:[{id:'mathematician',name:'Math',model:'local',skills:[]}]}:path==='/api/health'?{ollama:'online',models:['local']}:{status:'pass',checks:[]}};
    }};
  vm.createContext(sandbox);for(const file of ['web/teaching.js','web/teaching-ui.js','web/app.js'])vm.runInContext(fs.readFileSync(file,'utf8'),sandbox);
  await new Promise(r=>setImmediate(r));
  element('teaching-method').value='worked-example';element('teaching-rationale').value='Concrete examples';element('teaching-success').value='Use fewer hints';element('teaching-start').onclick();
  assert.equal(JSON.parse(raw).experiments.length,1);assert.equal(element('teaching-start').disabled,true);
  element('prompt').value='What is a vector space?';await element('chat').onsubmit({preventDefault(){}});
  assert.match(requests[0].messages.at(-1).content,/LARPUS_TEACHING_V1/);
  assert.equal(vm.runInContext('history[0].content',sandbox),'What is a vector space?','hidden metadata must not enter saved transcript');
  assert.equal(JSON.parse(raw).experiments[0].replies,1);assert.equal(element('teaching-accept').disabled,false);
  failStream=true;element('prompt').value='Another question';await element('chat').onsubmit({preventDefault(){}});
  assert.equal(JSON.parse(raw).experiments[0].replies,1,'held replies do not consume trial');
  element('teaching-review').value='Useful for new problems';element('teaching-accept').onclick();assert.equal(JSON.parse(raw).profiles[0].versions.length,1);
  element('teaching-version').value='0';element('teaching-review').value='Compare default';element('teaching-restore').onclick();assert.equal(JSON.parse(raw).profiles[0].versions.length,2);
  element('prompt').value='Preserve draft';element('teaching-suggest').onclick();assert.equal(element('prompt').value,'Preserve draft');
  assert.match(element('teaching-status').textContent,/draft/);
  element('prompt').value='';element('teaching-suggest').onclick();assert.match(element('prompt').value,/observable success/);assert.equal(JSON.parse(raw).profiles[0].versions.length,2);
}
integration().then(()=>console.log('Teaching lifecycle, storage failure, scope isolation and chat/UI integration passed.')).catch(e=>{console.error(e);process.exitCode=1;});
