const $ = id => document.getElementById(id);
let history = [], busy = false, personas = [], skills = [];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
function state(value) { $('core-state').textContent = `● ${value}`; }
function message(role, content) {
  const el = document.createElement('div'); el.className = `message ${role}`;
  const label = document.createElement('strong'); label.textContent = role === 'user' ? 'YOU / TRANSMIT' : 'LARPUS / RESPONSE';
  el.append(label, document.createTextNode(content)); $('messages').append(el); $('messages').scrollTop = $('messages').scrollHeight;
}
function reset() { history = []; $('messages').replaceChildren(); $('notice').textContent = 'New session. Conversation stays in browser memory only.'; }
function setBusy(value) { busy = value; for (const id of ['send','persona','skill','clear']) $(id).disabled = value; state(value ? 'THINKING' : 'STANDBY'); }
async function api(path, body) {
  const r = await fetch(path, body ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
  if(r.status===401){location.replace('/login');throw Error('Session expired');}
  const data = await r.json(); if (!r.ok) throw Error(data.error || 'Gateway request failed'); return data;
}
$('persona').addEventListener('change', () => {reset(); const p = personas.find(p => p.id === $('persona').value); $('description').textContent = p.description; $('model').textContent = p.model; refreshSkills(p);});
function refreshSkills(persona) {
  const options=[new Option('Persona only',''),...skills.filter(s=>(persona.skills||[]).includes(s.id)).map(s=>new Option(s.name,s.id))];
  $('skill').replaceChildren(...options);$('skill').disabled=false;
}
$('skill').onchange=reset;
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
  try { const result = await api('/api/chat',{persona:$('persona').value,messages:next,skill:$('skill').value||null}); history = [...next,{role:'assistant',content:result.content}]; message('assistant',result.content); }
  catch (err) { $('notice').textContent = err.message; $('prompt').value = content; }
  finally {setBusy(false); $('prompt').focus();}
};
$('mic').onclick = async () => {try {await api('/api/voice', {action:'listen'});} catch(e) {$('notice').textContent=e.message;}};
async function boot() {
  try { const data = await api('/api/personas'); personas = data.personas; skills=data.skills||[]; $('persona').replaceChildren(...personas.map(p=>new Option(p.name,p.id))); $('persona').disabled=false; const p=personas[0]; $('description').textContent=p.description; $('model').textContent=p.model;refreshSkills(p);
    const h = await api('/api/health'); $('connection').textContent = h.ollama === 'online' ? '● OLLAMA ONLINE' : '○ OLLAMA OFFLINE';
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
