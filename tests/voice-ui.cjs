// Browser-state regression tests without microphone hardware or extra packages.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const controls={};
function element(id){return controls[id]??=( {value:'',checked:false,disabled:false,textContent:'',options:[],querySelector(){return this;},setAttribute(){},replaceChildren(...o){this.options=o;},focus(){},click(){this.onclick?.();},requestSubmit(){this.submissions=(this.submissions||0)+1;}} );}
for(const id of ['mic','notice','voice-status','voice-record','voice-pause','voice-repeat','voice-mode','voice-speed','voice-speed-label','voice-review','voice-output','mic-device','mic-refresh','prompt','chat','clear','persona'])element(id);
element('voice-mode').value='push';element('voice-speed').value='1';element('voice-review').checked=true;element('voice-output').checked=true;
let now=2000;const delays=[];
let requested=[],requests=[],audios=[],processor,reply={transcript:'A useful question.'};
class Audio{constructor(){this.paused=true;this.currentTime=0;audios.push(this);}play(){this.paused=false;this.onplay?.();return Promise.resolve();}pause(){this.paused=true;this.onpause?.();}}
class AudioContext{constructor(){this.sampleRate=16000;}resume(){return Promise.resolve();}createMediaStreamSource(){return {connect(){},disconnect(){}};}createScriptProcessor(){return processor={connect(){},disconnect(){}};}createGain(){return {gain:{value:1},connect(){},disconnect(){}};}close(){return Promise.resolve();}}
const sandbox={document:{getElementById:element},window:{addEventListener(){}},navigator:{mediaDevices:{async getUserMedia(options){requested.push(options);return {getTracks(){return [{stop(){}}];}};},async enumerateDevices(){return [{kind:'audioinput',deviceId:'usb',label:'USB mic'}];},addEventListener(){}}},Audio,AudioContext,Option:function(text,value){this.text=text;this.value=value;},URL:{createObjectURL(){return 'blob:local';},revokeObjectURL(){}},Blob,Uint8Array,Float32Array,DataView,ArrayBuffer,performance:{now(){return now;}},btoa:s=>Buffer.from(s,'binary').toString('base64'),atob:s=>Buffer.from(s,'base64').toString('binary'),Event:class{},busy:false,setTimeout:(fn,ms)=>{delays.push(ms);setImmediate(fn);},api:async(path,data)=>{requests.push(data);return data.action==='synthesize'?{audio:'AAA='}:reply;}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync('web/voice.js','utf8'),sandbox);
const voice=sandbox.window.larpusVoice,tick=()=>new Promise(r=>setImmediate(r));
function frames(count,amplitude){for(let i=0;i<count;i++)processor.onaudioprocess({inputBuffer:{getChannelData(){return new Float32Array(2048).fill(amplitude);}}});}
(async()=>{
 await tick();element('mic-device').value='usb';await element('mic').onclick();
 assert.equal(requested[0].audio.deviceId.exact,'usb');assert.equal(voice.enabled,true);
 element('voice-record').onclick();frames(8,0);element('voice-record').onclick();await tick();assert.equal(requests.length,0,'silence must not be submitted');
 element('voice-record').onclick();frames(8,0.1);element('voice-record').onclick();await tick();
 assert.equal(element('prompt').value,'A useful question.');assert.equal(element('chat').submissions||0,0,'review prevents automatic sending');
 now+=2000;element('prompt').value='';reply={transcript:'',no_speech:true};element('voice-record').onclick();frames(8,0.1);element('voice-record').onclick();await tick();assert.equal(element('prompt').value,'');
 const playing=voice.play({content:'An approved reply.',audio:'AAA='});await tick();
 const audio=audios.at(-1);audio.currentTime=2;voice.pause();assert.equal(audio.paused,true);assert.equal(element('voice-pause').textContent,'RESUME AUDIO');
 element('voice-mode').value='handsfree';element('voice-mode').onchange();
 frames(8,0.1);frames(8,0);assert.equal(requests.length,2,'paused playback must not be captured even in hands-free mode');
 element('voice-mode').value='push';element('voice-mode').onchange();
 voice.pause();assert.equal(audio.paused,false);assert.equal(audio.currentTime,2);element('voice-speed').value='1.2';element('voice-speed').oninput();assert.equal(audio.playbackRate,1.2);
 audio.onended();await playing;
 voice.stop();assert.equal(voice.enabled,false);const replay=voice.repeat();await tick();assert.equal(audios.length,2,'replay works with mic off');audios.at(-1).onended();await replay;
 const oldReply=voice.repeat('An older displayed reply.');await tick();assert.equal(requests.at(-1).action,'synthesize');assert.equal(requests.at(-1).text,'An older displayed reply.');audios.at(-1).onended();await oldReply;
 const cancel=voice.play({content:'Another reply.',audio:'AAA='});await tick();voice.stopPlayback();await cancel;assert.equal(element('voice-pause').disabled,true);
 now+=2000;await element('mic').onclick();let resolveReply;reply=new Promise(resolve=>{resolveReply=resolve;});
 element('voice-record').onclick();frames(8,0.1);element('voice-record').onclick();voice.stop();
 resolveReply({transcript:'A stale result.'});await tick();assert.equal(element('prompt').value,'','muting must discard pending recognition');
 voice.beginReply();voice.enqueueSpeech('First checked sentence. ');await tick();
 const first=audios.at(-1),before=audios.length;
 voice.enqueueSpeech('Second checked sentence. ');voice.enqueueSpeech('Third checked sentence.');await tick();
 assert.equal(audios.length,before,'queued speech must not interrupt current audio');
 assert.equal(requests.at(-1).text,'Second checked sentence. ','only one sentence is prepared ahead');
 voice.pause();assert.equal(first.paused,true);voice.finishReply('First checked sentence. Second checked sentence. Third checked sentence.');
 await tick();assert.equal(audios.length,before,'paused audio holds the queue');
 voice.pause();first.onended();await tick();
 assert.equal(audios.length,before+1);assert.equal(requests.at(-1).text,'Third checked sentence.');
 voice.stopPlayback();await tick();assert.equal(audios.length,before+1,'cancelling discards prepared audio');
 const whole=voice.repeat();await tick();assert.equal(requests.at(-1).text,'First checked sentence. Second checked sentence. Third checked sentence.');audios.at(-1).onended();await whole;
 now+=2000;await element('mic').onclick();element('voice-mode').value='handsfree';element('voice-interrupt').checked=true;reply={transcript:'A new utterance.'};
 let interrupted=0;sandbox.window.larpusCancelGeneration=()=>{interrupted++;voice.stopPlayback();};
 const barge=voice.play({content:'Interruptible reply.',audio:'AAA='});await tick();
 const interruptedAudio=audios.at(-1);frames(3,0.1);await barge;assert.equal(interrupted,1);assert.equal(interruptedAudio.paused,true);
 frames(8,0.1);frames(8,0);await tick();assert.equal(element('prompt').value,'A new utterance.','new speech remains available for transcript review');
 assert.equal(element('chat').submissions||0,0,'interruption never bypasses transcript review');voice.stop();
 const punctuationStart=requests.length;
 voice.beginReply();voice.enqueueSpeech('...');voice.enqueueSpeech('---');await tick();
 assert.equal(requests.length,punctuationStart,'punctuation-only chunks must not be synthesized');
 voice.enqueueSpeech('Speech continues after the separator.');await tick();
 assert.equal(requests.at(-1).text,'Speech continues after the separator.');
 voice.finishReply('Speech continues after the separator.');audios.at(-1).onended();await tick();voice.stop();
 const originalApi=sandbox.api;let finishSynthesis;
 sandbox.api=async(path,data)=>{requests.push(data);if(data.text==='Still synthesizing.')return new Promise(resolve=>{finishSynthesis=resolve;});return {audio:'AAA='};};
 voice.beginReply();voice.enqueueSpeech('Still synthesizing.');await tick();
 const queuedCount=requests.length;
 const staleReplay=voice.repeat('Stale replay.'),latestReplay=voice.repeat('Latest replay.');await tick();
 assert.equal(requests.length,queuedCount,'manual replay must wait for unfinished synthesis');
 finishSynthesis({audio:'AAA='});await tick();
 assert.equal(requests.at(-1).text,'Latest replay.');
 assert.equal(requests.slice(queuedCount).some(r=>r.text==='Stale replay.'),false,'superseded replay must not reach the worker');
 audios.at(-1).onended();await Promise.all([staleReplay,latestReplay]);voice.stop();sandbox.api=originalApi;
 // Skip-and-continue: a held sentence (422) must not end the rest of the reply.
 const fail=(status,retryAfter=0)=>Object.assign(Error(status===422?'Speech held by local output DLP.':'Too many requests. Try again shortly.'),{status,retryAfter});
 let options=[];const played=()=>audios.length;
 sandbox.api=async(path,data,opts)=>{requests.push(data);options.push(opts);if(data.text==='Held sentence.')throw fail(422);return {audio:'AAA='};};
 element('notice').textContent='';voice.beginReply();
 for(const t of ['One sentence.','Held sentence.','Three sentence.','Four sentence.'])voice.enqueueSpeech(t);
 let base=played();
 for(let i=0;i<6;i++){await tick();if(played()>base){audios.at(-1).onended();base=played();}}
 const spoken=requests.slice(-4).map(r=>r.text);
 assert.deepEqual(spoken,['One sentence.','Held sentence.','Three sentence.','Four sentence.'],'later sentences still reach synthesis');
 assert.match(element('notice').textContent,/1 spoken part skipped/);
 assert.ok(options.every(o=>o&&o.abortable===false),'speech requests opt out of the chat abort signal');
 voice.finishReply('done');voice.stop();
 // 429 then 200: one retry honouring Retry-After, capped at 5 s.
 let attempts=0;delays.length=0;
 sandbox.api=async(path,data)=>{requests.push(data);if(data.text==='Busy once.' && attempts++===0)throw fail(429,60);return {audio:'AAA='};};
 voice.beginReply();voice.enqueueSpeech('Busy once.');for(let i=0;i<4;i++)await tick();
 assert.equal(attempts,2,'exactly one retry');assert.deepEqual(delays,[5000],'Retry-After 60 s is capped at 5 s');
 audios.at(-1).onended();await tick();voice.stop();
 // 503 twice: retried once, then skipped, and the next sentence still plays.
 let busyCalls=0;delays.length=0;
 sandbox.api=async(path,data)=>{requests.push(data);if(data.text==='Always busy.'){busyCalls++;throw fail(503,2);}return {audio:'AAA='};};
 voice.beginReply();voice.enqueueSpeech('Always busy.');voice.enqueueSpeech('After busy.');for(let i=0;i<6;i++)await tick();
 assert.equal(busyCalls,2);assert.deepEqual(delays,[2000]);assert.equal(requests.at(-1).text,'After busy.');
 audios.at(-1).onended();await tick();voice.stop();
 // Replay skips a held part and still reads the remaining passage.
 const longPart='Held part '+'word '.repeat(420),rest='The replay continues here.';
 sandbox.api=async(path,data)=>{requests.push(data);if(data.text.startsWith('Held part'))throw fail(422);return {audio:'AAA='};};
 element('notice').textContent='';const before2=played();
 const skipping=voice.repeat(longPart+rest);for(let i=0;i<4;i++)await tick();
 assert.equal(played(),before2+1,'remaining replay part plays after a held part');assert.ok(requests.at(-1).text.endsWith(rest));
 audios.at(-1).onended();await skipping;assert.match(element('notice').textContent,/Replay: 1 spoken part skipped/);
 sandbox.api=originalApi;
 console.log('Voice UI: mic selection, silence/review gates, pause/resume, speed, replay, cancellation, skip-and-continue and bounded retry passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
