function failureText(data){const id=typeof data.error_id==='string'&&/^[a-f0-9]{16}$/.test(data.error_id)?` / diagnostic ${data.error_id}`:'';return (data.error||'Gateway request failed')+id;}
// Request preferences never grant tools or alter mandatory security policy.
function executionRequest(){
  const profile=document.getElementById('execution-profile')?.value||'verified';
  const interaction=document.getElementById('execution-interaction')?.value||'conversation';
  if(profile==='verified'&&interaction==='conversation')return {};
  return {execution:{profile,interaction,...(profile==='diagnostic'?{base:document.getElementById('execution-base')?.value||'verified'}:{})}};
}
function browserClock(){return globalThis.performance?.now()??Date.now();}
function recordFirstRender(node,started){
  if('firstDomUpdateMs' in node.dataset)return;
  node.dataset.firstDomUpdateMs=Math.max(0,browserClock()-started).toFixed(3);
  // A frame callback is an opportunity to render, not proof of physical paint.
  requestAnimationFrame(()=>{node.dataset.firstRenderOpportunityMs=Math.max(0,browserClock()-started).toFixed(3);});
}
function showModel(tag){tag=window.larpusSelectedModel||tag;$('model').textContent=({'qwen3.5:27b-q4_K_M':'Larpus 3.5 27B Q4','qwen3.8:27b-q4_K_M':'Larpus 3.8 27B Q4','larpus3.8:27b-q4':'Larpus 3.8 27B Q4'})[tag]||tag;$('model').title=tag;}
const $ = id => document.getElementById(id);
let history = [], busy = false, personas = [], skills = [];
let conversation=window.LarpusConversation?new window.LarpusConversation():null,lastUsage=null;
let teaching=null,modelSwitch=null,pipelineSwitch=null;
let requestController=null,localMemory=null,chatId=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);
const session=window.bindLarpusSession?window.bindLarpusSession({element:$,fetch:(...args)=>fetch(...args),
 onExpired:()=>{window.larpusVoice?.stopPlayback();setBusy(busy);$('notice').textContent='Session expired. Sign in above; your conversation and draft stay here.';},
 onRestored:()=>{setBusy(busy);$('notice').textContent='Signed in. Review your draft and submit when ready.';if(!personas.length)boot();else{refreshConnection();refreshHealth();modelSwitch?.refresh();}}
}):null;
function sessionResponse(response){if(session)return session.check(response);if(response.status===401)throw Error('Session expired. Your conversation is retained. Sign in from another tab, then retry.');return response;}
function pipeline(value){$('pipeline-status').textContent=value;state(value);}
function saveChat(){if(!localMemory)return;try{localMemory.save({id:chatId,title:(history[0]?.content||'Conversation').slice(0,80),persona:$('persona').value,skill:$('skill').value,messages:history,...(conversation?{record:conversation.record,through:conversation.through}:{}),updated:new Date().toISOString()});memoryMenu();}catch(e){$('memory-status').textContent=e.message;}}
function stopGeneration(){requestController?.abort();window.larpusVoice?.stopPlayback();}
window.larpusCancelGeneration=stopGeneration;window.larpusPipeline=pipeline;
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
function state(value) { $('core-state').textContent = `● ${value}`; }
function message(role, content) {
  const el = document.createElement('div'); el.className = `message ${role}`;
  const label = document.createElement('strong'); label.textContent = role === 'user' ? 'YOU / TRANSMIT' : 'LARPUS / RESPONSE';
  const text=document.createTextNode(content);el.append(label,text);let replay;
  if(role==='assistant'){replay=document.createElement('button');replay.type='button';replay.className='replay-reply';replay.textContent='REPLAY REPLY';replay.onclick=()=>window.larpusVoice?.repeat(text.textContent);el.append(replay);}
  $('messages').append(el); $('messages').scrollTop = $('messages').scrollHeight;
  return {text,label,replay};
}
function contextUsage(usage) {
  lastUsage=usage;
  const meter=$('context-meter'),label=$('context-label');
  if(!usage){meter.value=0;label.textContent='No measurement yet / 131,072 tokens';return;}
  const {capacity,prompt_tokens:prompt,output_tokens:output,omitted_messages:omitted}=usage;
  if(![4096,16384,131072,262144].includes(capacity) || !Number.isInteger(prompt) || !Number.isInteger(output) || prompt<0 || prompt>capacity || output<0 || output>capacity)return;
  const total=prompt+output;meter.max=capacity;meter.value=Math.min(total,capacity);
  label.textContent=`Latest request: ${total.toLocaleString()} / ${capacity.toLocaleString()} tokens (${Math.round(total/capacity*100)}%)`;
  $('context-detail').textContent=`${prompt.toLocaleString()} input + ${output.toLocaleString()} output. Up to 1,024 output tokens requested. ${Number.isInteger(omitted)&&omitted>0?`${omitted} older messages omitted from model input. `:''}Full chat stays visible; older turns may leave model context.`;
}
function reset() { window.larpusVoice?.stopPlayback(); saveChat(); chatId=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9); history = [];conversation=window.LarpusConversation?new window.LarpusConversation():null;compressionDisplay(); contextUsage(null); $('context-detail').textContent='Measured after a reply; includes instructions and selected references.'; $('messages').replaceChildren(); $('notice').textContent = 'New chat. Previously saved conversations remain in LOCAL CHATS.'; }
function setBusy(value) { busy = value;modelSwitch?.controls();pipelineSwitch?.controls(); teaching?.busy(value); for (const id of ['send','persona','skill','clear']) $(id).disabled = value; $('stop-generation').disabled=!value;for(const id of ['load-chat','delete-chat','delete-memory','save-chats','compress-chat','export-handoff','import-handoff'])$(id).disabled=value;$('send').disabled=value||!!window.larpusModelSwitching||!!session?.locked;$('compress-chat').disabled=value||!!window.larpusModelSwitching||!!session?.locked;pipeline(value?'WAITING / RETRIEVING / PREPARING MODEL':window.larpusVoice?.playing?'SPEAKING':'STANDBY'); }
async function api(path, body) {
  const r = await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),...(requestController?{signal:requestController.signal}:{})} : {});
  sessionResponse(r);
  const data = await r.json(); if (!r.ok) throw Error(failureText(data)); return data;
}
$('persona').addEventListener('change', () => {const p = personas.find(p => p.id === $('persona').value); $('description').textContent = p.description; showModel(p.model); $('skill').value='';$('skill-search').value='';refreshSkills(p);teaching?.refresh();$('notice').textContent='Persona changed. Chat retained; the next reply uses the new role.';});
function refreshSkills(persona) {
  if(!persona)return;
  const selected=$('skill').value,query=$('skill-search').value.toLowerCase().trim();
  const allowed=skills.filter(s=>(persona.skills||[]).includes(s.id));
  const options=[new Option('Persona only',''),...allowed.filter(s=>s.id===selected || (s.name+' '+s.description).toLowerCase().includes(query)).map(s=>new Option(s.name,s.id))];
  $('skill').replaceChildren(...options);if(allowed.some(s=>s.id===selected))$('skill').value=selected;$('skill').disabled=false;
}
$('skill').onchange=()=>{teaching?.refresh();$('notice').textContent='Skill changed. Chat retained; the next reply uses the selected skill.';};
$('clear').onclick = reset;
$('stop-generation').onclick=stopGeneration;
$('skill-search').oninput=()=>refreshSkills(personas.find(p=>p.id===$('persona').value));
const logout=document.createElement('button');logout.textContent='LOCK STATION';logout.id='logout';logout.type='button';
document.querySelector('header').append(logout);
logout.onclick=async()=>{try{await api('/api/logout',{});location.replace('/login');}catch(e){$('notice').textContent=e.message;}};
document.querySelectorAll('.suggestion').forEach(b => b.onclick = () => {$('prompt').value = b.dataset.prompt; $('prompt').focus();});
$('prompt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {e.preventDefault(); $('chat').requestSubmit();} });
$('chat').onsubmit = async e => {
  e.preventDefault(); const content = $('prompt').value.trim(); if (busy || session?.locked || window.larpusModelSwitching || !content || !personas.length) return;
  if (history.length >= (conversation?400:38)) { $('notice').textContent = 'Transcript limit reached. Export a handoff, then start a new conversation from it.'; return; }
  $('messages').querySelector('.empty')?.remove(); message('user', content); $('prompt').value = ''; $('notice').textContent = ''; setBusy(true);
  const next = [...history,{role:'user',content}];
  let reply,full='',complete=false;
  requestController=typeof AbortController==='function'?new AbortController():null;const started=Date.now();
  const requestExecution=executionRequest(),diagnosticStarted=requestExecution.execution?.profile==='diagnostic'?browserClock():null;
  window.larpusVoice?.beginReply();
  try {
    const ownerQuestion=localMemory?localMemory.context(content):content;
    const adaptation=teaching?teaching.request(ownerQuestion):{question:ownerQuestion,token:null};
    const question=adaptation.question;
    if(conversation?.needs(history,question,lastUsage))await compressConversation();
    const outgoing=conversation?conversation.wire(history,question):[...next.slice(0,-1),{role:'user',content:question}];
    const response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},...(requestController?{signal:requestController.signal}:{}),body:JSON.stringify({persona:$('persona').value,messages:outgoing,skill:$('skill').value||null,...requestExecution})});
    sessionResponse(response);
    if(!response.ok)throw Error(failureText(await response.json()));
    pipeline('GENERATING / WAITING FOR CHECKED TEXT');
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    try{
      while(true){
        const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});
        if(buffer.length>400000)throw Error('Reply stream exceeded limits');
        let end;
        while((end=buffer.indexOf('\n'))>=0){
          const event=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);
          if(event.type==='error')throw Error(failureText(event));
          if(event.type==='text'){
            if(complete || typeof event.content!=='string' || (full.length+event.content.length)>65536)throw Error('Invalid reply stream');
            if(!event.content)continue;
            if(!full)$('pipeline-status').textContent=`FIRST CHECKED TEXT / ${((Date.now()-started)/1000).toFixed(1)}s`;
            state('GENERATING');full+=event.content;
            if(!reply){reply=message('assistant','');reply.replay.disabled=true;}
            reply.text.textContent=full;$('messages').scrollTop=$('messages').scrollHeight;
            if(diagnosticStarted!==null)recordFirstRender(reply.text,diagnosticStarted);
            window.larpusVoice?.enqueueSpeech(event.content);
          }else if(event.type==='done'){
            complete=true;
            if(event.context)contextUsage(event.context);
            if(reply && Array.isArray(event.sources) && event.sources.length){
              const refs=document.createElement('div');refs.className='reply-sources';refs.textContent='LOCAL REFERENCES';
              for(const source of event.sources){
                const card=document.createElement('details'),heading=document.createElement('summary'),body=document.createElement('p');
                const age=source.snapshot?Math.floor((Date.now()-Date.parse(source.snapshot))/86400000):NaN;
                const provenance=source.provenance||{};
                const authors=Array.isArray(provenance.document_authors)&&provenance.document_authors.length?provenance.document_authors.join('; '):'unknown / not inferred from citations';
                const identity=`Document authors: ${authors}\nPublished: ${provenance.published_on||'unknown'} / Revised: ${provenance.revised_on||'unknown'}\nSection: ${provenance.section||'unknown'}\n`;
                heading.textContent=`[${source.id}] ${source.title}`;
                body.textContent=`${identity}Snapshot ${source.snapshot||'date unavailable'}${Number.isFinite(age)?` / ${age} days old`:''} / ${source.locator}\n${source.url}\n\n${source.preview||'Preview unavailable for this reference.'}\nA snapshot is not proof of current support or pricing.`;
                card.append(heading,body);refs.append(card);
              }
              if(event.citation_check){const check=document.createElement('p');check.textContent=`Citation identifiers: ${event.citation_check.status}. This checks identifiers, not whether every claim is supported.`;refs.append(check);}
              $('messages').children[$('messages').children.length-1].append(refs);
            }
          }
          else throw Error('Invalid reply stream');
        }
        if(done)break;
      }
    }finally{await reader.cancel();reader.releaseLock();}
    if(!complete || !full.trim() || buffer.trim())throw Error('Reply stream ended early');
    history=[...next,{role:'assistant',content:full}];reply.replay.disabled=false;saveChat();teaching?.completed(adaptation.token);
    window.larpusVoice?.finishReply(full);
  }
  catch (err) {if(err.name!=='AbortError')window.larpusVoice?.stopPlayback();if(reply)reply.label.textContent='LARPUS / INCOMPLETE — NOT SAVED';$('notice').textContent=err.name==='AbortError'?'Stopped. Incomplete reply excluded from chat memory.':err.message;$('prompt').value=content;}
  finally {requestController=null;setBusy(false); $('prompt').focus();}
};


function compressionDisplay(){
  if(!conversation)return;
  $('context-record').textContent=conversation.record?JSON.stringify(conversation.record,null,2):'No summary.';
  $('compression-status').textContent=`${conversation.through/2} completed turns represented by a machine-generated record; ${Math.max(0,history.length-conversation.through)/2} recent turns remain verbatim. Full transcript stays visible.`;
}
async function compressConversation(keep=8){
  if(!conversation||!history.length)return false;
  const changed=await conversation.compress(history,async(batch,index,total)=>{
    pipeline(`COMPRESSING / ${index} OF ${total}`);
    return api('/api/context/compress',{persona:$('persona').value,...batch});
  },keep);
  if(changed){lastUsage=null;compressionDisplay();saveChat();}
  return changed;
}
function bindHandoff(){
  if(!conversation)return;
  const task=fn=>async()=>{if(busy)return;setBusy(true);requestController=typeof AbortController==='function'?new AbortController():null;window.larpusVoice?.stopPlayback();try{await fn();}catch(e){$('notice').textContent=e.name==='AbortError'?'Compression stopped. Previous conversation record retained.':e.message;}finally{requestController=null;setBusy(false);}};
  $('compress-chat').onclick=task(()=>compressConversation(0));
  $('export-handoff').onclick=task(async()=>{
    await compressConversation(8);if(!conversation.record&&history.length)await compressConversation(0);
    const data=conversation.handoff(history,$('persona').value,$('skill').value),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),link=document.createElement('a');
    link.href=url;link.download='larpus-handoff.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('notice').textContent='Handoff exported. Review its machine-generated record and uncertainties before reusing it.';
  });
  $('import-handoff').onclick=()=>{if(!busy)$('handoff-file').click();};
  $('handoff-file').onchange=async()=>{
    if(busy)return;const file=$('handoff-file').files?.[0];if(!file)return;
    try{
      if(file.size>70000)throw Error('Handoff file exceeds limit');
      const data=window.LarpusConversation.handoff(JSON.parse(await file.text())),persona=personas.find(p=>p.id===data.persona);
      if(!persona||data.skill&&!(persona.skills||[]).includes(data.skill))throw Error('Handoff role or skill is not installed');
      if(!window.confirm('Start a new chat from this handoff? Export the current chat first if you need to retain it.'))return;
      reset();history=data.recent.map(m=>({...m}));conversation=new window.LarpusConversation(data.record,0);
      $('persona').value=persona.id;$('description').textContent=persona.description;showModel(persona.model);$('skill-search').value='';refreshSkills(persona);$('skill').value=data.skill;teaching?.refresh();
      for(const m of history)message(m.role,m.content);compressionDisplay();saveChat();
      $('notice').textContent='Handoff staged as untrusted conversation data. The server filters it on the next request; permissions remain unchanged.';
    }catch(e){$('notice').textContent='Handoff not loaded: '+e.message;}
    finally{$('handoff-file').value='';}
  };
  compressionDisplay();
}

function memoryMenu(){
  if(!localMemory)return;
  const chosen=$('saved-chat').value;$('saved-chat').replaceChildren(new Option('Choose a saved conversation',''),...localMemory.data.sessions.map(s=>new Option(s.title,s.id)));$('saved-chat').value=chosen;
  $('save-chats').checked=localMemory.data.enabled;
  $('remembered-notes').replaceChildren(...localMemory.data.notes.map((n,i)=>{const row=document.createElement('div'),text=document.createElement('p'),remove=document.createElement('button');text.textContent=`${n.text} / owner entered ${n.created.slice(0,10)}`;remove.textContent='FORGET';remove.type='button';remove.onclick=()=>{try{localMemory.forget(i);memoryMenu();}catch(e){$('memory-status').textContent=e.message;}};row.append(text,remove);return row;}));
  $('memory-status').textContent=localMemory.error||`Chat saving ${localMemory.data.enabled?'on':'off'} / ${localMemory.data.sessions.length} saved / ${localMemory.data.notes.length} remembered notes. Browser storage is not encrypted by LARPUS.`;
}
function bindMemory(){
  if(!window.LarpusStore)return;
  try{localMemory=new window.LarpusStore(localStorage);}catch(e){$('memory-status').textContent='Browser storage unavailable. Chat still works.';return;}
  const action=fn=>()=>{try{fn();memoryMenu();}catch(e){$('memory-status').textContent=e.message;}};
  $('save-chats').onchange=action(()=>{localMemory.enable($('save-chats').checked);saveChat();});
  $('add-note').onclick=action(()=>{localMemory.remember($('remember-note').value);$('remember-note').value='';});
  $('delete-chat').onclick=action(()=>{if(window.confirm('Delete this saved conversation from this browser?'))localMemory.remove($('saved-chat').value);});
  $('delete-memory').onclick=action(()=>{if(window.confirm('Delete all saved chats and remembered notes from this browser?'))localMemory.clear();});
  $('load-chat').onclick=action(()=>{
    if(busy)return;const saved=localMemory.data.sessions.find(s=>s.id===$('saved-chat').value);if(!saved)return;
    saveChat();window.larpusVoice?.stopPlayback();history=saved.messages.map(m=>({...m}));chatId=saved.id;$('messages').replaceChildren();for(const m of history)message(m.role,m.content);
    const persona=personas.find(p=>p.id===saved.persona);if(persona){$('persona').value=persona.id;$('description').textContent=persona.description;showModel(persona.model);$('skill-search').value='';refreshSkills(persona);$('skill').value=(persona.skills||[]).includes(saved.skill)?saved.skill:'';}
    teaching?.refresh();
    conversation=window.LarpusConversation?new window.LarpusConversation(saved.record||null,saved.through||0):null;compressionDisplay();contextUsage(null);$('notice').textContent='Saved chat loaded. Model context is rebuilt on the next turn; older turns may be omitted.';
  });
  $('export-memory').onclick=action(()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(localMemory.data,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='larpus-local-memory.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  memoryMenu();
}

async function refreshConnection(){
  const p=personas.find(p=>p.id===$('persona').value)||personas[0];
  try{
    const h = await api('/api/health'); $('connection').textContent = h.ollama === 'online' ? `OLLAMA ONLINE / ${h.model_processors?.[h.active_model||p.model] || 'PLACEMENT UNKNOWN'}` : 'OLLAMA OFFLINE';
    if(h.ollama === 'offline') $('notice').textContent='Start local Ollama to open the inference channel.';
    else if(!h.models.includes(h.active_model||p.model)) $('notice').textContent=`Install ${p.model} in local Ollama before chatting.`;
  }catch(e){$('connection').textContent='GATEWAY UNAVAILABLE';$('notice').textContent=e.message;}
}
async function boot() {
  try { const data = await api('/api/personas'); personas = data.personas; skills=data.skills||[]; $('persona').replaceChildren(...personas.map(p=>new Option(p.name,p.id))); $('persona').disabled=false; const p=personas.find(p=>p.id==='home-assistant')||personas[0]; $('persona').value=p.id; $('description').textContent=p.description; showModel(p.model);refreshSkills(p);bindMemory();bindHandoff();
    if(window.bindLarpusTeaching)teaching=window.bindLarpusTeaching({scope:()=>window.LarpusTeaching.scope($('persona').value,$('skill').value),isBusy:()=>busy,prompt:$('prompt')});
    if(window.bindLarpusModelSwitch){modelSwitch=window.bindLarpusModelSwitch({api,element:$,isBusy:()=>busy||!!session?.locked,onState:s=>{window.larpusModelSwitching=s.phase!=='ready';window.larpusSelectedModel=s.models?.find(m=>m.id===s.active_id)?.tag;showModel(p.model);$('send').disabled=busy||window.larpusModelSwitching||!!session?.locked;$('compress-chat').disabled=busy||window.larpusModelSwitching||!!session?.locked;}});await modelSwitch.refresh();setInterval(()=>modelSwitch.refresh(),2500);}
    if(window.bindLarpusPipeline){pipelineSwitch=window.bindLarpusPipeline({api,element:$,isBusy:()=>busy||!!session?.locked||!!window.larpusModelSwitching});await pipelineSwitch.refresh();setInterval(()=>pipelineSwitch.refresh(),15000);}
    await refreshConnection();
  } catch(e) {$('connection').textContent='○ GATEWAY UNAVAILABLE'; $('notice').textContent=e.message;}
  if(window.katex) {
    katex.render(String.raw`\iiint_T 1\,dV = 2\pi^2Rr^2 \approx 25.266`, $('equation'), {throwOnError:false});
    katex.render(String.raw`T=\{(x,y,z):(\sqrt{x^2+y^2}-R)^2+z^2\le r^2\}`, $('torus-domain'), {throwOnError:false});
  }
}
// Depth-sorted torus surface: sweep tube sections around the major circle.
// Reference dimensions R = 2, r = .8 give volume approximately 25.266.
const canvas = $('torus'), ctx = canvas.getContext('2d');
let angle = 0, elapsed = 0, last = 0;
function draw(now) {
  const dt = Math.min((now - last) / 1000, .05); last = now;
  if (!reduced.matches) { angle += dt * (busy ? .45 : .12); elapsed += dt * (busy ? 1.5 : 1); }
  // Fill for 6 seconds, hold the completed surface for 1 second, repeat.
  const fill = reduced.matches ? 1 : Math.min((elapsed % 7) / 6, 1);
  const percentage = Math.floor(fill * 100);
  if ($('forming').textContent !== `forming ${percentage}%`) $('forming').textContent = `forming ${percentage}%`;
  const rect = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
  const width = Math.round(rect.width * dpr), height = Math.round(rect.height * dpr);
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, rect.width, rect.height);
  const project = (u, v) => {
    const x = (2 + .8 * Math.cos(v)) * Math.cos(u + angle);
    const y = (2 + .8 * Math.cos(v)) * Math.sin(u + angle), z = .8 * Math.sin(v);
    const yy = y * .48 - z * .88, depth = y * .88 + z * .48;
    const scale = Math.min(rect.width, rect.height) * .16 * 7 / (7 + depth);
    return [rect.width / 2 + x * scale, rect.height / 2 + yy * scale, depth];
  };
  const sections = 96, rings = 32, cells = [];
  for (let i = 0; i < sections; i++) {
    const u = i * 2 * Math.PI / sections;
    // The last section grows continuously, rather than popping into place.
    const coverage = Math.max(0, Math.min(1, fill * sections - i));
    for (let j = 0; j < rings; j++) {
      const v = j * 2 * Math.PI / rings;
      const points = [project(u,v), project(u+2*Math.PI/sections,v), project(u+2*Math.PI/sections,v+2*Math.PI/rings), project(u,v+2*Math.PI/rings)];
      cells.push({points, depth:points.reduce((sum,p)=>sum+p[2],0)/4, i, j, coverage, u, v});
    }
  }
  cells.sort((a,b)=>b.depth-a.depth);
  const path = points => { ctx.beginPath(); points.forEach((p,i)=>i ? ctx.lineTo(p[0],p[1]) : ctx.moveTo(p[0],p[1])); ctx.closePath(); };
  for (const cell of cells) {
    // Dim scaffold remains visible ahead of the filling surface.
    path(cell.points); ctx.strokeStyle = 'rgba(80,160,175,.12)'; ctx.lineWidth = .45; ctx.stroke();
    if (!cell.coverage) continue;
    const end = cell.u + 2 * Math.PI / sections * cell.coverage;
    const points = [project(cell.u,cell.v),project(end,cell.v),project(end,cell.v+2*Math.PI/rings),project(cell.u,cell.v+2*Math.PI/rings)];
    path(points);
    const checker = (Math.floor(cell.i/8) + Math.floor(cell.j/8)) % 2;
    const light = Math.round(39 + 13 * Math.cos(cell.v - .8));
    ctx.fillStyle = checker ? `hsl(186 75% ${light}%)` : `hsl(207 52% ${12 + light*.12}%)`;
    ctx.fill(); ctx.strokeStyle = 'rgba(130,246,244,.23)'; ctx.lineWidth = .5; ctx.stroke();
  }
  requestAnimationFrame(draw);
}
boot(); requestAnimationFrame(draw);

async function refreshHealth() {
  try {
    const report=await api('/api/station-health');
    $('health-summary').textContent=`STATION HEALTH / ${report.status.toUpperCase()}`;
    const rows=(report.checks||[]).map(check=>{
      const row=document.createElement('p');
      row.textContent=`${check.name} / ${check.status.toUpperCase()} - ${check.message}`;
      return row;
    });
    if(report.message){const row=document.createElement('p');row.textContent=report.message;rows.push(row);}
    $('health-checks').replaceChildren(...rows);
  } catch(e) {$('health-summary').textContent='STATION HEALTH / UNAVAILABLE';}
}
refreshHealth(); setInterval(refreshHealth,30000);
