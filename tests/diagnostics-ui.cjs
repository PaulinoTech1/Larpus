const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const helper=source.split(/\r?\n/)[0];
const context=vm.createContext({});vm.runInContext(helper,context);
assert.equal(context.failureText({error:'Interrupted',error_id:'a'.repeat(16)}),'Interrupted / diagnostic '+'a'.repeat(16));
assert.equal(context.failureText({error:'Interrupted',error_id:'C:/private/token'}),'Interrupted');
assert.equal(context.failureText({}),'Gateway request failed');
console.log('Diagnostic UI: correlation IDs shown; invalid IDs withheld.');
