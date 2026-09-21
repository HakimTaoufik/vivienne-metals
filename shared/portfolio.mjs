export const STORAGE_KEY='vivienne.portfolio.v1';
export function validateLedger(transactions,products) {
  if(!Array.isArray(transactions)||transactions.length>20000)throw Error('Journal invalide ou trop volumineux.');
  const ids=new Set(),known=new Set(products.map(p=>p.id)),counts=new Map();
  const result=transactions.map((t,index)=>{
    if(!t||typeof t!=='object'||typeof t.id!=='string'||t.id.length>100||!t.id||ids.has(t.id))throw Error('Identifiant absent ou en double.');
    ids.add(t.id);
    if(!known.has(t.product)||!['buy','sell'].includes(t.type))throw Error('Produit ou opération invalide.');
    for(const k of ['quantity','unitPriceCents','feesCents'])if(!Number.isSafeInteger(t[k])||t[k]<(k==='feesCents'?0:1))throw Error('Quantité, prix ou frais invalides.');
    if(t.quantity>100000||t.unitPriceCents>1000000000||t.feesCents>1000000000)throw Error('Montant trop élevé.');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(t.date)||!Number.isFinite(Date.parse(t.date))||new Date(t.date).toISOString().slice(0,10)!==t.date)throw Error('Date invalide.');
    if(t.date>new Date().toISOString().slice(0,10))throw Error('Une opération réelle ne peut pas être future.');
    if(t.note!=null&&(typeof t.note!=='string'||t.note.length>500))throw Error('Note trop longue.');
    return {id:t.id,product:t.product,type:t.type,quantity:t.quantity,unitPriceCents:t.unitPriceCents,feesCents:t.feesCents,date:t.date,note:t.note||'',order:index};
  }).sort((a,b)=>a.date.localeCompare(b.date)||a.order-b.order);
  for(const t of result) {
    const n=(counts.get(t.product)||0)+(t.type==='buy'?t.quantity:-t.quantity);
    if(n<0)throw Error(`Vente supérieure au stock disponible à la date du ${t.date}.`);
    counts.set(t.product,n);
  }
  return result.map(({order,...t})=>t);
}
export function ledger(transactions,products) {
  const tx=validateLedger(transactions,products),holdings=new Map();let realizedCents=0;
  for(const t of tx) {
    if(!holdings.has(t.product))holdings.set(t.product,{product:t.product,lots:[],quantity:0,costCents:0,realizedCents:0});
    const h=holdings.get(t.product);
    if(t.type==='buy')h.lots.push({quantity:t.quantity,costCents:t.quantity*t.unitPriceCents+t.feesCents,date:t.date});
    else {
      let left=t.quantity,basis=0;
      while(left){const lot=h.lots[0],take=Math.min(left,lot.quantity),cost=take===lot.quantity?lot.costCents:Math.round(lot.costCents*take/lot.quantity);basis+=cost;lot.costCents-=cost;lot.quantity-=take;left-=take;if(!lot.quantity)h.lots.shift();}
      const profit=t.quantity*t.unitPriceCents-t.feesCents-basis;h.realizedCents+=profit;realizedCents+=profit;
    }
    h.quantity=h.lots.reduce((a,l)=>a+l.quantity,0);h.costCents=h.lots.reduce((a,l)=>a+l.costCents,0);
  }
  return {holdings:[...holdings.values()],realizedCents,transactions:tx};
}
export function loadLedger(storage,products) {
  const raw=storage.getItem(STORAGE_KEY);if(raw===null)return [];
  let data;try{data=JSON.parse(raw);}catch{throw Error('Sauvegarde illisible. Exportez les données brutes avant toute restauration.');}
  if(data.schemaVersion!==1)throw Error('Version de sauvegarde non prise en charge.');
  return validateLedger(data.transactions,products);
}
export function persistLedger(storage,transactions,products) {
  const valid=validateLedger(transactions,products);
  const raw=JSON.stringify({schemaVersion:1,exportedAt:new Date().toISOString(),transactions:valid});
  storage.setItem(STORAGE_KEY,raw); // Atomic browser write. Caller updates memory only after success.
  return valid;
}
export function importLedger(raw,current,products,mode='merge') {
  if(raw.length>10000000)throw Error('Fichier trop volumineux.');
  const data=JSON.parse(raw);if(data.schemaVersion!==1)throw Error('Version de sauvegarde non prise en charge.');
  const incoming=validateLedger(data.transactions,products);
  if(mode==='replace')return incoming;
  const map=new Map(current.map(t=>[t.id,t]));
  for(const t of incoming){if(map.has(t.id)&&JSON.stringify(map.get(t.id))!==JSON.stringify(t))throw Error('Conflit entre deux opérations de même identifiant.');map.set(t.id,t);}
  return validateLedger([...map.values()],products);
}
