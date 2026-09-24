// One self-contained, offline replay of the real collected snapshot.
// The calculation clock is explicitly frozen; no prices or history are generated.
import {readFile,writeFile} from 'node:fs/promises';
const data={};
for(const path of ['config/products.json','config/dealers.json','config/settings.json','data/market.json','data/notifications.json']){
  try{data['./'+path]=JSON.parse(await readFile('dist/'+path,'utf8'));}catch{if(!path.endsWith('notifications.json'))throw Error('Missing demo input '+path);}
}
const stamp=data['./data/market.json'].generatedAt;
let modules='';
for(const [id,path] of [['model','shared/model.mjs'],['portfolio','shared/portfolio.mjs'],['chart','web/chart.mjs']]){
  const code=await readFile(path,'utf8'),names=[...code.matchAll(/export\s+(?:function|const|class)\s+(\w+)/g)].map(m=>m[1]);
  modules+=`const ${id}=(()=>{${code.replace(/\bexport\s+/g,'')}\nreturn {${names.join(',')}};})();\n`;
}
let app=await readFile('web/app.mjs','utf8');
app=app.replace(/^import \{([^}]+)\} from '([^']+)';$/gm,(_,names,path)=>`const {${names.replace(/\s+as\s+/g,':')}}=${path.includes('model')?'model':path.includes('portfolio')?'portfolio':'chart'};`);
app=app.replace(/^async function json\(path\).*$/m,'async function json(path){if(!(path in stored))throw Error("Fichier absent de la démonstration");return structuredClone(stored[path]);}');
app=app.replace('now=()=>new Date().toISOString()',`now=()=>${JSON.stringify(stamp)}`).replace('Date.now()-period*86400000',`Date.parse(${JSON.stringify(stamp)})-period*86400000`);
app=app.replaceAll('vivienne.settings.v1','vivienne.demo.settings.v1');modules=modules.replaceAll('vivienne.portfolio.v1','vivienne.demo.portfolio.v1');
let html=await readFile('web/index.html','utf8');
html=html.replace(/<meta http-equiv="Content-Security-Policy"[^>]+>/,'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'nonce-vivienne-demo\'; style-src \'unsafe-inline\'; img-src data:; object-src \'none\'; form-action \'none\'">');
html=html.replace(/<link[^>]+>/g,'').replace(/<script type="module"[^>]+><\/script>/,'');
html=html.replace('</head>',`<style>${await readFile('web/styles.css','utf8')}</style></head>`);
html=html.replace('<main id="main" tabindex="-1">',`<main id="main" tabindex="-1"><div class="notice">Démonstration locale · relevé réel du ${stamp}. Prix et heure des calculs figés pour vérifier les comparaisons. Le journal de démonstration est séparé du site.</div>`);
const script=`(()=>{const stored=${JSON.stringify(data)};${modules}\n${app}\n})();`.replace(/<\/script/gi,'<\\/script');
html=html.replace('</body>',`<script nonce="vivienne-demo">${script}</script></body>`);
await writeFile('dist/demo.html',html);
console.log('Built offline replay from '+stamp);
