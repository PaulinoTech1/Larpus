const $ = id => document.getElementById(id);
let history = [], busy = false, personas = [], skills = [];
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
  const meter=$('context-meter'),label=$('context-label');
  if(!usage){meter.value=0;label.textContent='No measurement yet / 4,096 tokens';return;}
  const {capacity,prompt_tokens:prompt,output_tokens:output,omitted_messages:omitted}=usage;
  if(capacity!==4096 || !Number.isInteger(prompt) || !Number.isInteger(output) || prompt<0 || prompt>capacity || output<0 || output>capacity)return;
  const total=prompt+output;meter.max=capacity;meter.value=Math.min(total,capacity);
  label.textContent=`Latest request: ${total.toLocaleString()} / ${capacity.toLocaleString()} tokens (${Math.round(total/capacity*100)}%)`;
  $('context-detail').textContent=`${prompt.toLocaleString()} input + ${output.toLocaleString()} output. Up to 1,024 output tokens requested. ${Number.isInteger(omitted)&&omitted>0?`${omitted} older messages omitted from model input. `:''}Full chat stays visible; older turns may leave model context.`;
}
function reset() { window.larpusVoice?.stopPlayback(); history = []; contextUsage(null); $('context-detail').textContent='Measured after a reply; includes instructions and selected references.'; $('messages').replaceChildren(); $('notice').textContent = 'New session. Conversation stays in browser memory only.'; }
function setBusy(value) { busy = value; for (const id of ['send','persona','skill','clear']) $(id).disabled = value; state(value ? 'THINKING' : 'STANDBY'); }
async function api(path, body) {
  const r = await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
  if(r.status===401){location.replace('/login');throw Error('Session expired');}
  const data = await r.json(); if (!r.ok) throw Error(data.error || 'Gateway request failed'); return data;
}
$('persona').addEventListener('change', () => {const p = personas.find(p => p.id === $('persona').value); $('description').textContent = p.description; $('model').textContent = p.model; refreshSkills(p);$('notice').textContent='Persona changed. Chat retained; the next reply uses the new role.';});
function refreshSkills(persona) {
  const options=[new Option('Persona only',''),...skills.filter(s=>(persona.skills||[]).includes(s.id)).map(s=>new Option(s.name,s.id))];
  $('skill').replaceChildren(...options);$('skill').disabled=false;
}
$('skill').onchange=()=>{$('notice').textContent='Skill changed. Chat retained; the next reply uses the selected skill.';};
$('clear').onclick = reset;
const logout=document.createElement('button');logout.textContent='LOCK STATION';logout.id='logout';logout.type='button';
document.querySelector('header').append(logout);
logout.onclick=async()=>{try{await api('/api/logout',{});location.replace('/login');}catch(e){$('notice').textContent=e.message;}};
document.querySelectorAll('.suggestion').forEach(b => b.onclick = () => {$('prompt').value = b.dataset.prompt; $('prompt').focus();});
$('prompt').addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {e.preventDefault(); $('chat').requestSubmit();} });
$('chat').onsubmit = async e => {
  e.preventDefault(); const content = $('prompt').value.trim(); if (busy || !content || !personas.length) return;
  if (history.length >= 38) { $('notice').textContent = 'Session limit reached. Reset to begin a new conversation.'; return; }
  $('messages').querySelector('.empty')?.remove(); message('user', content); $('prompt').value = ''; $('notice').textContent = ''; setBusy(true);
  const next = [...history,{role:'user',content}];
  let reply,full='',complete=false;
  window.larpusVoice?.beginReply();
  try {
    const response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({persona:$('persona').value,messages:next,skill:$('skill').value||null})});
    if(response.status===401){location.replace('/login');throw Error('Session expired');}
    if(!response.ok)throw Error((await response.json()).error||'Gateway request failed');
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    try{
      while(true){
        const {value,done}=await reader.read();buffer+=decoder.decode(value||new Uint8Array(),{stream:!done});
        if(buffer.length>400000)throw Error('Reply stream exceeded limits');
        let end;
        while((end=buffer.indexOf('\n'))>=0){
          const event=JSON.parse(buffer.slice(0,end));buffer=buffer.slice(end+1);
          if(event.type==='error')throw Error(event.error||'Response withheld');
          if(event.type==='text'){
            if(complete || typeof event.content!=='string' || (full.length+event.content.length)>65536)throw Error('Invalid reply stream');
            full+=event.content;
            if(!reply){reply=message('assistant','');reply.replay.disabled=true;}
            reply.text.textContent=full;$('messages').scrollTop=$('messages').scrollHeight;
            window.larpusVoice?.enqueueSpeech(event.content);
          }else if(event.type==='done'){
            complete=true;
            if(event.context)contextUsage(event.context);
            if(reply && Array.isArray(event.sources) && event.sources.length){
              const refs=document.createElement('div');refs.className='reply-sources';
              refs.textContent='LOCAL REFERENCES\n'+event.sources.map(s=>`[${s.id}] ${s.title}\nSnapshot ${s.snapshot} / ${s.locator}\n${s.url}`).join('\n\n');
              $('messages').children[$('messages').children.length-1].append(refs);
            }
          }
          else throw Error('Invalid reply stream');
        }
        if(done)break;
      }
    }finally{await reader.cancel();reader.releaseLock();}
    if(!complete || !full.trim() || buffer.trim())throw Error('Reply stream ended early');
    history=[...next,{role:'assistant',content:full}];reply.replay.disabled=false;
    window.larpusVoice?.finishReply(full);
  }
  catch (err) {window.larpusVoice?.stopPlayback();if(reply)reply.label.textContent='LARPUS / INCOMPLETE — NOT SAVED';$('notice').textContent=err.message;$('prompt').value=content;}
  finally {setBusy(false); $('prompt').focus();}
};

async function boot() {
  try { const data = await api('/api/personas'); personas = data.personas; skills=data.skills||[]; $('persona').replaceChildren(...personas.map(p=>new Option(p.name,p.id))); $('persona').disabled=false; const p=personas.find(p=>p.id==='home-assistant')||personas[0]; $('persona').value=p.id; $('description').textContent=p.description; $('model').textContent=p.model;refreshSkills(p);
    const h = await api('/api/health'); $('connection').textContent = h.ollama === 'online' ? `OLLAMA ONLINE / ${h.model_processors?.[p.model] || 'PLACEMENT UNKNOWN'}` : 'OLLAMA OFFLINE';
    if(h.ollama === 'offline') $('notice').textContent='Start local Ollama to open the inference channel.';
    else if(!h.models.includes(p.model)) $('notice').textContent=`Install ${p.model} in local Ollama before chatting.`;
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
