// Same pure model runs in the browser, backtests, and scheduled notifications.
export const DEFAULTS = Object.freeze({lookbackDays:90,minDays:30,zThreshold:2,maxPremiumPct:8,maxSpreadPct:10,minEdgePct:1,buyFeePct:.5,sellFeePct:.5,taxPct:0,fixedFeeCents:0,tradeQuantity:1,budgetCents:500000,maxAgeHours:6,cooldownHours:24,alertEnabled:false});
const limits = {lookbackDays:[30,730],minDays:[10,365],zThreshold:[1,6],maxPremiumPct:[-20,100],maxSpreadPct:[0,100],minEdgePct:[0,50],buyFeePct:[0,30],sellFeePct:[0,30],taxPct:[0,50],fixedFeeCents:[0,10000000],tradeQuantity:[1,100000],budgetCents:[1,1000000000],maxAgeHours:[.25,48],cooldownHours:[1,720]};
export function settings(input={}) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('Paramètres invalides.');
  const s = {...DEFAULTS,...input};
  for(const [k,[lo,hi]] of Object.entries(limits)) if(typeof s[k]!=='number'||!Number.isFinite(s[k])||s[k]<lo||s[k]>hi) throw Error(`Paramètre invalide : ${k}`);
  for(const k of ['lookbackDays','minDays','tradeQuantity','fixedFeeCents','budgetCents']) if(!Number.isInteger(s[k])) throw Error(`${k} doit être entier.`);
  if(s.minDays>s.lookbackDays) throw Error('La fenêtre doit couvrir le minimum de jours.');
  if(typeof s.alertEnabled!=='boolean') throw Error('Activation invalide.');
  return Object.fromEntries(Object.keys(DEFAULTS).map(k=>[k,s[k]]));
}
const dayFormatter=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'});
export function parisDay(value) { return dayFormatter.format(new Date(value)); }
export function median(a) { if(!a.length)return null; const s=[...a].sort((x,y)=>x-y),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2; }
export function robust(values, value) { const center=median(values); if(center===null)return {center:null,scale:null,z:null}; const scale=Math.max(.25,1.4826*median(values.map(x=>Math.abs(x-center))));return {center,scale,z:(value-center)/scale}; }
export const premium = (price,melt) => Number.isFinite(price)&&price>0&&Number.isFinite(melt)&&melt>0 ? (price/melt-1)*100 : null;
export function fresh(q,now,maxAgeHours) { const age=new Date(now)-new Date(q.observedAt);return Number.isFinite(age)&&age>=-60000&&age<=maxAgeHours*3600000; }
export function costs(ask,bid,qty,s) {
  const buy = ask==null?null:Math.round(ask*qty*(1+s.buyFeePct/100)+s.fixedFeeCents);
  const sell = bid==null?null:Math.round(bid*qty*(1-(s.sellFeePct+s.taxPct)/100)-s.fixedFeeCents);
  return {buy,sell,edgePct:buy>0&&sell!=null?(sell/buy-1)*100:null};
}
export function meltForQuote(q,product,spots=[]) {
  if(Number.isFinite(q.meltCents)&&q.meltCents>0)return q.meltCents;
  const eligible=spots.filter(s=>s.metal===product.metal&&new Date(s.observedAt)<=new Date(q.observedAt)&&new Date(q.observedAt)-new Date(s.observedAt)<=6*3600000);
  const spot=eligible.sort((a,b)=>new Date(b.observedAt)-new Date(a.observedAt))[0];
  return spot?Math.round(spot.eurPerGram*product.fineGrams*100):null;
}
// Keep each side's own timestamp, minimum and provenance; never refresh an old bid using a new ask.
export function dealerRows(quotes,product,now,s,health=[]) {
  const map=new Map(),bad=new Set(health.filter(h=>h.status!=='ok').map(h=>h.id));
  for(const q of [...quotes].filter(q=>q.product===product).sort((a,b)=>new Date(a.observedAt)-new Date(b.observedAt))) {
    if(!map.has(q.dealer))map.set(q.dealer,{dealer:q.dealer,product,ask:null,bid:null});
    const r=map.get(q.dealer);
    for(const side of ['ask','bid']) if(q[side]!=null) r[side]={...q,valid:fresh(q,now,s.maxAgeHours)&&!bad.has(q.source),value:q[side]};
  }
  return [...map.values()];
}
function minimumOK(q,side,qty) { const min=q[side==='ask'?'minBuy':'minSell'];return Number.isInteger(min)&&min>0&&qty>=min; }
function training(history,q,product,spots,s) {
  const day=parisDay(q.observedAt),cutoff=new Date(q.observedAt)-s.lookbackDays*86400000,days=new Map();
  for(const h of [...history].sort((a,b)=>new Date(a.observedAt)-new Date(b.observedAt))) {
    if(h.dealer!==q.dealer||h.product!==q.product||parisDay(h.observedAt)>=day||new Date(h.observedAt)<cutoff)continue;
    const melt=meltForQuote(h,product,spots);if(!melt)continue;
    const d=parisDay(h.observedAt),row=days.get(d)||{};
    for(const side of ['ask','bid'])if(h[side])row[side]=premium(h[side],melt);
    days.set(d,row);
  }
  return {ask:[...days.values()].map(d=>d.ask).filter(Number.isFinite),bid:[...days.values()].map(d=>d.bid).filter(Number.isFinite)};
}
export function analyze(market,product,input={},now=new Date().toISOString()) {
  const s=settings(input),rows=dealerRows(market.quotes,product.id,now,s,market.health),spots=[...(market.spotHistory||[]),...(market.spots||[])];
  const signals=[];
  for(const row of rows) for(const side of ['ask','bid']) {
    const q=row[side];if(!q)continue;
    const type=side==='ask'?'buy':'sell',melt=meltForQuote(q,product,spots),p=premium(q.value,melt);
    const train=training(market.history||[],q,product,spots,s),stat=robust(train[side],p??0);
    const pair=row.ask?.valid&&row.bid?.valid?costs(row.ask.value,row.bid.value,s.tradeQuantity,s):null;
    const spread=pair?.edgePct==null?null:-pair.edgePct;
    const reasons=[];
    if(!q.valid)reasons.push('Cours périmé ou source en erreur');
    if(q.spotObservedAt&&!fresh({observedAt:q.spotObservedAt},now,s.maxAgeHours))reasons.push('Spot périmé');
    if(q.spotSource&&(market.health||[]).some(h=>h.id===q.spotSource&&h.status!=='ok'))reasons.push('Source du spot en erreur');
    if(p==null)reasons.push('Spot contemporain indisponible');
    if(!minimumOK(q,side,s.tradeQuantity))reasons.push('Quantité minimale non vérifiée ou non atteinte');
    if(train[side].length<s.minDays)reasons.push(`Historique insuffisant : ${train[side].length}/${s.minDays} jours`);
    let edge=null;
    if(type==='buy') {
      const entry=costs(q.value,null,s.tradeQuantity,s).buy;
      if(entry>s.budgetCents)reasons.push('Budget dépassé');
      if(p!=null&&p>s.maxPremiumPct)reasons.push('Prime trop élevée');
      if(spread==null||spread>s.maxSpreadPct)reasons.push('Écart achat/revente trop élevé ou incomplet');
      if(!row.bid||!minimumOK(row.bid,'bid',s.tradeQuantity))reasons.push('Quantité de revente non vérifiée');
      if(stat.z==null||stat.z>-s.zThreshold)reasons.push('Prime pas assez basse dans son historique');
      if(train.bid.length>=s.minDays&&melt) {
        const typicalBid=melt*(1+median(train.bid)/100);
        edge=costs(q.value,typicalBid,s.tradeQuantity,s).edgePct;
      }
      if(edge==null||edge<s.minEdgePct)reasons.push('Marge estimée après frais insuffisante');
    } else {
      if(stat.z==null||stat.z<s.zThreshold)reasons.push('Prime de rachat pas assez élevée');
      if(melt&&stat.center!=null) {
        const typicalBid=melt*(1+stat.center/100);
        const net=costs(null,q.value,s.tradeQuantity,s).sell;
        edge=(net/(typicalBid*s.tradeQuantity)-1)*100;
      }
      if(edge==null||edge<s.minEdgePct)reasons.push('Avantage sur le rachat habituel insuffisant après frais');
    }
    signals.push({type,product:product.id,dealer:q.dealer,price:q.value,observedAt:q.observedAt,url:q.url,
      premiumPct:p,z:stat.z,days:train[side].length,spreadPct:spread,edgePct:edge,
      excellent:reasons.length===0,reasons,quantity:s.tradeQuantity,method:'robust-premium-v1'});
  }
  return {signals,rows};
}
export function crossDealer(market,product,input={},now=new Date().toISOString()) {
  const s=settings(input),rows=dealerRows(market.quotes,product.id,now,s,market.health);
  const asks=rows.map(r=>r.ask).filter(q=>q?.valid&&minimumOK(q,'ask',s.tradeQuantity));
  const bids=rows.map(r=>r.bid).filter(q=>q?.valid&&minimumOK(q,'bid',s.tradeQuantity));
  const ask=asks.sort((a,b)=>a.value-b.value)[0],bid=bids.sort((a,b)=>b.value-a.value)[0];
  if(!ask||!bid)return null;
  const c=costs(ask.value,bid.value,s.tradeQuantity,s);
  const synchronized=Math.abs(new Date(ask.observedAt)-new Date(bid.observedAt))<=15*60000;
  return {...c,buyDealer:ask.dealer,sellDealer:bid.dealer,excellent:synchronized&&c.buy<=s.budgetCents&&c.edgePct>=s.minEdgePct,quantity:s.tradeQuantity,synchronized,
    note:'Écart indicatif à confirmer : état, stock, quantité, fiscalité et simultanéité.'};
}

export function backtest(market,product,input={}) {
  const s=settings(input),history=[...(market.history||[])].filter(q=>q.product===product.id).sort((a,b)=>new Date(a.observedAt)-new Date(b.observedAt));
  const grouped=new Map();for(const q of history){const d=parisDay(q.observedAt);if(!grouped.has(d))grouped.set(d,[]);grouped.get(d).push(q);}
  let cash=s.budgetCents,position=null,pending=null,peak=cash,maxDrawdown=0;const trades=[],equity=[];
  const days=[...grouped.keys()].sort();
  for(const [i,day] of days.entries()) {
    const quotes=grouped.get(day),at=quotes.at(-1).observedAt;
    const rows=dealerRows(quotes,product.id,at,s,[]);
    if(pending) {
      const list=rows.map(r=>r[pending.type==='buy'?'ask':'bid']).filter(q=>q?.valid&&minimumOK(q,pending.type==='buy'?'ask':'bid',s.tradeQuantity));
      const q=list.sort((a,b)=>pending.type==='buy'?a.value-b.value:b.value-a.value)[0];
      if(q) {
        const fill=Math.round(q.value*(pending.type==='buy'?1.0025:.9975));
        if(pending.type==='buy'&&!position) {
          const cost=costs(fill,null,s.tradeQuantity,s).buy;
          if(cost<=cash){cash-=cost;position={entry:cost,index:i,day};}
        } else if(pending.type==='sell'&&position) {
          const proceeds=costs(null,fill,s.tradeQuantity,s).sell;
          cash+=proceeds;trades.push({entryDay:position.day,exitDay:day,pnlCents:proceeds-position.entry});position=null;
        }
      }
      pending=null;
    }
    const signal=analyze({...market,quotes,health:[],history:history.filter(h=>parisDay(h.observedAt)<day)},product,s,at).signals;
    if(position&&(signal.some(x=>x.type==='sell'&&x.excellent)||i-position.index>=30))pending={type:'sell'};
    if(!position&&signal.some(x=>x.type==='buy'&&x.excellent))pending={type:'buy'};
    const bid=rows.map(r=>r.bid).filter(q=>q?.valid).sort((a,b)=>b.value-a.value)[0];
    const value=position?(bid?costs(null,bid.value*.9975,s.tradeQuantity,s).sell:null):0;
    if(value!==null){const total=cash+value;peak=Math.max(peak,total);maxDrawdown=Math.max(maxDrawdown,(peak-total)/peak*100);equity.push({day,valueCents:total});}
  }
  return {days:days.length,trades,openPosition:!!position,pendingOrder:!!pending,equity,maxDrawdownPct:maxDrawdown,
    returnPct:equity.length?(equity.at(-1).valueCents/s.budgetCents-1)*100:null,
    enoughHistory:days.length>=s.minDays+2,note:'Simulation chronologique ; exécution à l’observation du jour suivant, glissement de 0,25 % par côté. Aucune garantie de rendement.'};
}
