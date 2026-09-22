import {readFile,readdir,copyFile,mkdir,rm,cp} from 'node:fs/promises';
import {join} from 'node:path';
import {settings} from '../shared/model.mjs';
const out='dist';
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
await cp('web',out,{recursive:true});await cp('shared',join(out,'shared'),{recursive:true});
await mkdir(join(out,'config'),{recursive:true});await mkdir(join(out,'data'),{recursive:true});
for(const name of ['products','dealers','settings']) {
  const raw=await readFile(`config/${name}.json`,'utf8');const parsed=JSON.parse(raw);if(name==='settings')settings(parsed);
  await copyFile(`config/${name}.json`,join(out,`config/${name}.json`));
}
const marketPath=process.env.MARKET_DATA_PATH||'data/market.json';
const market=JSON.parse(await readFile(marketPath,'utf8'));if(market.schemaVersion!==1||!Array.isArray(market.quotes))throw Error('Invalid market snapshot');
await copyFile(marketPath,join(out,'data/market.json'));
try{await copyFile(process.env.NOTIFICATION_STATUS_PATH||'data/notifications.json',join(out,'data/notifications.json'));}catch{}
console.log('Built static GitHub Pages dashboard. Public files contain market data only.');
