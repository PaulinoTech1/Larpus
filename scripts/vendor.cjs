const fs = require('node:fs');
fs.mkdirSync('web/vendor/katex', {recursive:true});
for (const file of ['katex.min.js','katex.min.css','fonts']) fs.cpSync(`node_modules/katex/dist/${file}`, `web/vendor/katex/${file}`, {recursive:true});
fs.copyFileSync('node_modules/katex/LICENSE', 'web/vendor/katex/LICENSE');
