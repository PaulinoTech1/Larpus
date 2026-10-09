const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const harness=fs.readFileSync('tests/chat-stream-ui.cjs','utf8').split("(async()=>{")[0].replace("addEventListener(){}", "addEventListener(name,fn){(this.listeners??={})[name]=fn;}");
const scope={require,console,Buffer,setImmediate,TextDecoder,Uint8Array};vm.createContext(scope);vm.runInContext(harness+"globalThis.makeApp=setup;",scope);
(async()=>{
 const app=scope.makeApp([{type:'text',content:'Remember the pilot. '},{type:'done',context:{capacity:4096,prompt_tokens:1000,output_tokens:24,omitted_messages:2}}]);
 await new Promise(r=>setImmediate(r));app.element('prompt').value='Keep this discussion';const done=app.element('chat').onsubmit({preventDefault(){}});await new Promise(r=>setImmediate(r));app.finish();await done;
 assert.equal(app.element('context-meter').value,1024);assert.match(app.element('context-label').textContent,/25%/);assert.match(app.element('context-detail').textContent,/2 older messages/);
 const before=vm.runInContext('JSON.stringify(history)',app.sandbox),visible=app.element('messages').children.length;
 app.element('skill').value='another-skill';app.element('skill').onchange();
 assert.equal(vm.runInContext('JSON.stringify(history)',app.sandbox),before);assert.equal(app.element('messages').children.length,visible);assert.match(app.element('notice').textContent,/Chat retained/);
 app.element('persona').value='home-assistant';app.element('persona').listeners.change();assert.equal(vm.runInContext('JSON.stringify(history)',app.sandbox),before);assert.equal(app.element('messages').children.length,visible);
 vm.runInContext("contextUsage({capacity:4096,prompt_tokens:-1,output_tokens:1})",app.sandbox);assert.equal(app.element('context-meter').value,1024);
 app.element('clear').onclick();assert.equal(vm.runInContext('history.length',app.sandbox),0);assert.equal(app.element('context-meter').value,0);
 console.log('Context UI: measured counts, invalid counts, retained skill conversation and explicit reset passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
