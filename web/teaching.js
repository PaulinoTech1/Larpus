// Owner-controlled, browser-local pedagogy. Model replies never mutate this store.
window.LarpusTeaching = class {
  static key='larpus-teaching-v1';
  static options={pace:['steady','slow','brisk'],depth:['balanced','foundations','advanced'],method:['mixed','direct','socratic','worked-example'],hints:['on-request','progressive'],challenge:['balanced','gentle','stretch']};
  static defaults(){return Object.fromEntries(Object.entries(this.options).map(([k,v])=>[k,v[0]]));}
  static settings(p){
    if(!p || Object.keys(p).sort().join()!==Object.keys(this.options).sort().join() || Object.entries(this.options).some(([k,v])=>!v.includes(p[k])))throw Error('Invalid teaching settings');
    return p;
  }
  static text(s,max=240){if(typeof s!=='string'||!s.trim()||s.length>max)throw Error('Add a nonempty note within '+max+' characters');return s.trim();}
  static valid(d){
    const exact=(v,keys)=>v&&Object.keys(v).sort().join()===keys.sort().join();
    const stamp=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(s)&&Number.isFinite(Date.parse(s));
    if(!exact(d,['version','profiles','experiments'])||d.version!==1||!Array.isArray(d.profiles)||d.profiles.length>24||!Array.isArray(d.experiments)||d.experiments.length>80)throw Error('Invalid or full teaching journal');
    const keys=new Set();
    for(const p of d.profiles){
      if(!exact(p,['scope','versions'])||!this.validScope(p.scope)||keys.has(p.scope)||!Array.isArray(p.versions)||!p.versions.length||p.versions.length>20)throw Error('Invalid teaching profile');keys.add(p.scope);
      p.versions.forEach((v,i)=>{if(!exact(v,['number','settings','at','reason'])||v.number!==i+1||!stamp(v.at))throw Error('Invalid profile version');this.settings(v.settings);this.text(v.reason);});
    }
    d.experiments.forEach((e,i)=>{
      if(!exact(e,['id','scope','settings','base','rationale','success','at','status','replies','feedback','review','closed'])||e.id!==i+1||!this.validScope(e.scope)||!Number.isInteger(e.base)||e.base<0||e.base>(d.profiles.find(p=>p.scope===e.scope)?.versions.length||0)||!stamp(e.at)||!['trial','accepted','rejected'].includes(e.status)||!Number.isInteger(e.replies)||e.replies<0||e.replies>3||!Array.isArray(e.feedback)||e.feedback.length>6)throw Error('Invalid experiment');
      this.settings(e.settings);this.text(e.rationale);this.text(e.success);
      for(const f of e.feedback){if(!exact(f,['reply','rating','note','at'])||!Number.isInteger(f.reply)||f.reply<1||f.reply>e.replies||!['helpful','mixed','unhelpful'].includes(f.rating)||!stamp(f.at))throw Error('Invalid feedback');this.text(f.note);}
      if(e.status==='trial'){if(e.review!==null||e.closed!==null)throw Error('Invalid open trial');}
      else {this.text(e.review);if(!stamp(e.closed)||e.status==='accepted'&&!e.replies)throw Error('Invalid trial review');}
    });
    const open=d.experiments.filter(e=>e.status==='trial');if(new Set(open.map(e=>e.scope)).size!==open.length)throw Error('Overlapping trials');
    if(JSON.stringify(d).length>160000)throw Error('Teaching journal full; export before resetting');return d;
  }
  static validScope(s){return typeof s==='string'&&/^[a-z][a-z0-9-]{0,63}\|(?:[a-z][a-z0-9-]{0,79})?$/.test(s);}
  static scope(persona,skill=''){const s=persona+'|'+skill;if(!this.validScope(s))throw Error('Invalid teaching scope');return s;}
  constructor(storage){this.storage=storage;this.raw=null;this.data={version:1,profiles:[],experiments:[]};this.read();}
  read(){try{this.raw=this.storage.getItem(window.LarpusTeaching.key);if(this.raw!==null){if(this.raw.length>160000)throw Error('Teaching journal too large');this.data=window.LarpusTeaching.valid(JSON.parse(this.raw));}this.error=null;}catch(e){this.error='Teaching storage unavailable: '+e.message;}}
  change(fn){
    if(this.error)throw Error('Stored journal unavailable. Reload or explicitly reset it after export.');
    if(this.storage.getItem(window.LarpusTeaching.key)!==this.raw)throw Error('Teaching journal changed in another tab. Reload before editing.');
    const next=JSON.parse(JSON.stringify(this.data));fn(next);window.LarpusTeaching.valid(next);
    const raw=JSON.stringify(next);this.storage.setItem(window.LarpusTeaching.key,raw);this.raw=raw;this.data=next;
  }
  profile(scope){return this.data.profiles.find(p=>p.scope===scope);}
  accepted(scope){return this.profile(scope)?.versions.at(-1)?.settings||window.LarpusTeaching.defaults();}
  trial(scope){return this.data.experiments.find(e=>e.scope===scope&&e.status==='trial');}
  start(scope,settings,rationale,success){
    if(!window.LarpusTeaching.validScope(scope))throw Error('Invalid teaching scope');window.LarpusTeaching.settings(settings);
    if(this.trial(scope))throw Error('Review the existing trial first');
    if(Object.keys(window.LarpusTeaching.options).every(k=>settings[k]===this.accepted(scope)[k]))throw Error('Change at least one setting for a trial');
    rationale=window.LarpusTeaching.text(rationale);success=window.LarpusTeaching.text(success);
    this.change(d=>d.experiments.push({id:d.experiments.length+1,scope,settings:{...settings},base:this.profile(scope)?.versions.length||0,rationale,success,at:new Date().toISOString(),status:'trial',replies:0,feedback:[],review:null,closed:null}));
  }
  request(scope,question){
    // Re-read on each request so another tab's accepted changes are respected.
    this.read();if(this.error)return {question,token:null};
    const e=this.trial(scope),trial=e&&e.replies<3,profile=trial?e.settings:this.accepted(scope);
    if(!trial&&!this.profile(scope))return {question,token:null};
    const wrapped='LARPUS_TEACHING_V1\n'+JSON.stringify({question,profile,mode:trial?'trial':'accepted'});
    if(wrapped.length>8000||question.length>7200)throw Error('Message and teaching preferences exceed the teaching input budget. Shorten the message.');
    return {question:wrapped,token:trial?{id:e.id,reply:e.replies+1}:null};
  }
  completed(token){if(!token)return;this.change(d=>{const e=d.experiments.find(e=>e.id===token.id);if(!e||e.status!=='trial'||e.replies!==token.reply-1||e.replies>=3)throw Error('Trial changed during this reply; progress not recorded');e.replies++;});}
  feedback(scope,rating,note){
    note=window.LarpusTeaching.text(note);this.change(d=>{const e=d.experiments.find(e=>e.scope===scope&&e.status==='trial');if(!e?.replies)throw Error('Complete a trial reply before giving feedback');e.feedback.push({reply:e.replies,rating,note,at:new Date().toISOString()});});
  }
  review(scope,accept,note){
    note=window.LarpusTeaching.text(note);this.change(d=>{
      const e=d.experiments.find(e=>e.scope===scope&&e.status==='trial');if(!e)throw Error('No trial to review');if(accept&&!e.replies)throw Error('Complete a trial reply before accepting');
      if(accept){let p=d.profiles.find(p=>p.scope===scope);if(!p){p={scope,versions:[]};d.profiles.push(p);}p.versions.push({number:p.versions.length+1,settings:{...e.settings},at:new Date().toISOString(),reason:note});}
      e.status=accept?'accepted':'rejected';e.review=note;e.closed=new Date().toISOString();
    });
  }
  restore(scope,number,note){
    note=window.LarpusTeaching.text(note);this.change(d=>{const p=d.profiles.find(p=>p.scope===scope);if(!p||!Number.isInteger(number)||number<0||number>=p.versions.length)throw Error('Choose an earlier version');if(d.experiments.some(e=>e.scope===scope&&e.status==='trial'))throw Error('Review the trial before restoring');p.versions.push({number:p.versions.length+1,settings:{...(number?p.versions[number-1].settings:window.LarpusTeaching.defaults())},at:new Date().toISOString(),reason:'Restore v'+number+': '+note});});
  }
  reset(){this.storage.removeItem(window.LarpusTeaching.key);this.data={version:1,profiles:[],experiments:[]};this.raw=null;this.error=null;}
};
