// A model may propose a trial in chat. Only these owner controls approve changes.
window.bindLarpusTeaching = ({scope, isBusy, prompt}) => {
  const el=id=>document.getElementById(id), panel=el('teaching-controls');
  let store;
  try{store=new window.LarpusTeaching(localStorage);}catch(e){el('teaching-status').textContent='Teaching storage unavailable; ordinary chat still works.';return null;}
  const fields=Object.keys(window.LarpusTeaching.options);
  for(const [key,values] of Object.entries(window.LarpusTeaching.options))el('teaching-'+key).replaceChildren(...values.map(v=>new Option(v.replaceAll('-',' '),v)));
  function refresh(){
    const key=scope(),trial=store.trial(key),p=store.profile(key),settings=trial?.settings||store.accepted(key);
    el('teaching-scope').textContent=key.split('|')[0]+' / '+(key.split('|')[1]||'persona only')+' (exact role and skill)';
    for(const field of fields)el('teaching-'+field).value=settings[field];
    el('teaching-version').replaceChildren(new Option('Default style / v0','0'),...(p?.versions||[]).map(v=>new Option('Version '+v.number+' / '+v.at.slice(0,10),String(v.number))));
    const journal=store.data.experiments.filter(e=>e.scope===key).slice().reverse().map(e=>{
      const row=document.createElement('p');row.textContent=`Trial ${e.id} / ${e.status} / ${e.replies} completed replies / ${e.at.slice(0,10)}\nSettings: ${JSON.stringify(e.settings)}\nWhy: ${e.rationale}\nSuccess criterion: ${e.success}\n${e.feedback.map(f=>`Reply ${f.reply}: ${f.rating} — ${f.note}`).join('\n')}${e.review?'\nReview: '+e.review:''}`;return row;
    });
    const versions=(p?.versions||[]).slice().reverse().map(v=>{const row=document.createElement('p');row.textContent=`Accepted v${v.number} / ${v.at.slice(0,10)}\n${JSON.stringify(v.settings)}\n${v.reason}`;return row;});
    el('teaching-journal').replaceChildren(...journal,...versions);
    el('teaching-status').textContent=store.error||`${p?'Accepted v'+p.versions.length:'Default style'}${trial?` / Trial ${trial.id}: ${trial.replies}/3 completed replies${trial.replies===3?'; trial paused, accepted style resumes until review':''}`:''}. Feedback is owner judgment, not proof of learning gains.`;
    busy(isBusy());
  }
  function busy(value){
    const trial=store.trial(scope()),p=store.profile(scope());
    panel.querySelectorAll('button, select, textarea, input').forEach(node=>{node.disabled=value;});
    for(const field of fields)el('teaching-'+field).disabled=value||!!trial||!!store.error;
    el('teaching-start').disabled=value||!!trial||!!store.error;
    el('teaching-accept').disabled=value||!trial?.replies||!!store.error;
    el('teaching-reject').disabled=value||!trial||!!store.error;
    el('teaching-feedback').disabled=value||!trial?.replies||!!store.error;
    el('teaching-restore').disabled=value||!!trial||!p||!!store.error;
  }
  const action=fn=>()=>{if(isBusy())return;try{fn();refresh();}catch(e){el('teaching-status').textContent=e.message;}};
  el('teaching-start').onclick=action(()=>store.start(scope(),Object.fromEntries(fields.map(f=>[f,el('teaching-'+f).value])),el('teaching-rationale').value,el('teaching-success').value));
  el('teaching-feedback').onclick=action(()=>{store.feedback(scope(),el('teaching-rating').value,el('teaching-review').value);el('teaching-review').value='';});
  el('teaching-accept').onclick=action(()=>{store.review(scope(),true,el('teaching-review').value);el('teaching-review').value='';});
  el('teaching-reject').onclick=action(()=>{store.review(scope(),false,el('teaching-review').value);el('teaching-review').value='';});
  el('teaching-restore').onclick=action(()=>{store.restore(scope(),Number(el('teaching-version').value),el('teaching-review').value);el('teaching-review').value='';});
  el('teaching-suggest').onclick=action(()=>{
    if(prompt.value.trim())throw Error('Send or clear your draft message before asking for a suggestion.');
    prompt.value='Suggest one teaching-style experiment for our selected subject. Use only these setting choices: '+JSON.stringify(window.LarpusTeaching.options)+'. Give a short rationale, a tradeoff, and an observable success criterion for a three-reply trial. Do not claim any saved change. I will choose the settings and approve the trial myself.';prompt.focus();
  });
  el('teaching-export').onclick=action(()=>{
    const url=URL.createObjectURL(new Blob([store.raw||JSON.stringify(store.data,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='larpus-teaching-journal.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  el('teaching-reset').onclick=action(()=>{if(window.confirm('Delete all teaching profiles and experiments in this browser? Export first to retain the journal. Chats and remembered notes remain.'))store.reset();});
  refresh();
  return {
    refresh:()=>{store.read();refresh();},busy,
    request:question=>{const result=store.request(scope(),question);refresh();return result;},
    completed:token=>{try{store.completed(token);refresh();}catch(e){el('teaching-status').textContent='Reply retained; journal update failed: '+e.message;}}
  };
};
