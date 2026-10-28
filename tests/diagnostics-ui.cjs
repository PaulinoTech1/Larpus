const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const helper=source.split(/\r?\n/)[0];
const context=vm.createContext({});vm.runInContext(helper,context);
assert.equal(context.failureText({error:'Interrupted',error_id:'a'.repeat(16)}),'Interrupted / diagnostic '+'a'.repeat(16));
assert.equal(context.failureText({error:'Interrupted',error_id:'C:/private/token'}),'Interrupted');
assert.equal(context.failureText({}),'Gateway request failed');

for(const [code,pattern] of Object.entries({inference_budget:/Wait a minute/,queue_full:/queue is full/,admission_timeout:/Timed out waiting/,cancellation_unconfirmed:/repeated retries may not recover/,inference_deadline:/exceeded its time limit/,model_switching:/model is switching/,broker_held:/Owner investigation/})){
 const message=context.failureText({code,error:'Generic broker refusal',error_id:'b'.repeat(16)});
 assert.match(message,pattern);assert.ok(message.includes(`(broker: ${code})`));assert.ok(message.endsWith(' / diagnostic '+'b'.repeat(16)));
}
for(const code of ['unknown_code','__proto__','toString'])assert.equal(context.failureText({code,error:'Existing failure'}),'Existing failure','unknown codes retain the original error');
assert.equal(context.failureText({code:'queue_full',error_id:'C:/private/token'}).includes('C:/private/token'),false);
console.log('Diagnostic UI: correlation IDs shown; invalid IDs withheld.');
