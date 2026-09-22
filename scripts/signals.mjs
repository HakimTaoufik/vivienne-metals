import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {dirname} from 'node:path';
import {analyze,crossDealer,settings} from '../shared/model.mjs';
const market=JSON.parse(await readFile(process.argv[2]||'data/market.json','utf8'));
const products=JSON.parse(await readFile('config/products.json','utf8'));
const config=settings(JSON.parse(await readFile('config/settings.json','utf8')));
const now=new Date().toISOString();
const signals=[];
for(const product of products) {
  signals.push(...analyze(market,product,config,now).signals.filter(s=>s.excellent));
  const cross=crossDealer(market,product,config,now);
  if(cross?.excellent) {
    const relevant=market.quotes.filter(q=>q.product===product.id&&[cross.buyDealer,cross.sellDealer].includes(q.dealer));
    signals.push({type:'spread',product:product.id,dealer:`${cross.buyDealer} → ${cross.sellDealer}`,price:null,edgePct:cross.edgePct,
      observedAt:relevant.map(q=>q.observedAt).sort()[0],url:relevant[0]?.url,excellent:true,quantity:config.tradeQuantity,method:'cross-dealer-net-v1'});
  }
}
const output=process.argv[3]||'private/signals.json';
await mkdir(dirname(output),{recursive:true});
await writeFile(output,JSON.stringify({schemaVersion:1,generatedAt:now,settings:config,signals},null,2)+'\n');
console.log(`${signals.length} eligible market signals; notifications ${config.alertEnabled?'enabled':'disabled'}.`);
