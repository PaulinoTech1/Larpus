// Spoken text must drop markdown, citations and author credits that stay on screen.
const fs=require('fs'),assert=require('assert');
const src=fs.readFileSync(__dirname+'/../web/voice.js','utf8');
const m=src.match(/function speakable\(text\)\{[\s\S]*?\n  \}/);
assert.ok(m,'speakable() present');
const speakable=eval('('+m[0]+')');
const out=speakable('## Answer\n**Approachability** lets a player steer outcomes (Blackwell, 1956) [pjm-blackwell-1956-vector-minimax].\n- Use `regret` tables, boss. See [the paper](https://msp.org/pjm/1956/6-1/p01.xhtml).');
for(const bad of ['#','*','`','[',']','(',')','Blackwell','1956','pjm-','http'])assert.ok(!out.includes(bad),'spoke '+bad+': '+out);
assert.ok(out.includes('Approachability lets a player steer outcomes.'),out);
assert.ok(out.includes('Use regret tables, boss.'),out);
assert.ok(out.includes('See the paper.'),out);
console.log('Speech text: markdown, citations and author credits stripped. '+JSON.stringify(out));