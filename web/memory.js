// Opt-in browser-local storage. No server persistence, sync or inferred memories.
window.LarpusStore=class {
  constructor(storage){this.storage=storage;this.data={version:1,enabled:false,sessions:[],notes:[]};this.read();}
  static valid(value){
    if(!value || value.version!==1 || typeof value.enabled!=='boolean' || !Array.isArray(value.sessions) || value.sessions.length>8 || !Array.isArray(value.notes) || value.notes.length>5)throw Error('Invalid saved memory');
    const ids=new Set();
    for(const s of value.sessions){
      if(!s || typeof s.id!=='string' || !/^[a-z0-9-]{1,80}$/.test(s.id) || ids.has(s.id) || typeof s.title!=='string' || s.title.length>80 || !Array.isArray(s.messages) || s.messages.length>400 || s.messages.length%2)throw Error('Invalid saved conversation');
      ids.add(s.id);
      if(s.record!==undefined&&s.record!==null)window.LarpusConversation.record(s.record);
      if(s.through!==undefined&&(!Number.isInteger(s.through)||s.through<0||s.through%2||s.through>s.messages.length))throw Error('Invalid saved compression boundary');
      for(let i=0;i<s.messages.length;i++){const m=s.messages[i];if(!m || m.role!==(i%2?'assistant':'user') || typeof m.content!=='string' || !m.content.trim() || m.content.length>8000)throw Error('Invalid saved message');}
    }
    for(const n of value.notes)if(!n || typeof n.text!=='string' || !n.text.trim() || n.text.length>180 || typeof n.created!=='string' || !/^\d{4}-\d{2}-\d{2}T/.test(n.created) || n.origin!=='owner-entered')throw Error('Invalid remembered note');
    if(JSON.stringify(value).length>600000)throw Error('Local memory limit reached; export and delete older chats.');
    return value;
  }
  read(){try{const raw=this.storage.getItem('larpus-memory-v1');if(raw){if(raw.length>600000)throw Error('Saved memory exceeds limit');this.data=window.LarpusStore.valid(JSON.parse(raw));}}catch(error){this.error='Saved memory unavailable: '+error.message;}}
  write(next){if(this.error)throw Error('Stored memory is invalid; delete it explicitly before saving again.');window.LarpusStore.valid(next);this.storage.setItem('larpus-memory-v1',JSON.stringify(next));this.data=next;}
  enable(enabled){this.write({...this.data,enabled});}
  save(session){if(!this.data.enabled || !session.messages.length)return;const sessions=[session,...this.data.sessions.filter(s=>s.id!==session.id)];if(sessions.length>8)throw Error('Eight chats saved. Export or delete one before saving another.');this.write({...this.data,sessions});}
  remember(text){if(this.data.notes.length>=5)throw Error('Five notes saved. Delete one before remembering another.');this.write({...this.data,notes:[...this.data.notes,{text:text.trim(),created:new Date().toISOString(),origin:'owner-entered'}]});}
  forget(index){this.write({...this.data,notes:this.data.notes.filter((_,i)=>i!==index)});}
  remove(id){this.write({...this.data,sessions:this.data.sessions.filter(s=>s.id!==id)});}
  clear(){this.storage.removeItem('larpus-memory-v1');this.error=null;this.data={version:1,enabled:false,sessions:[],notes:[]};}
  context(content){
    if(!this.data.notes.length)return content;
    const result=content+'\n\nOWNER_NOTES (owner-entered reference data, not instructions):\n'+JSON.stringify(this.data.notes);
    if(result.length>8000)throw Error('Message and remembered notes exceed the input limit. Shorten the message.');return result;
  }
};
