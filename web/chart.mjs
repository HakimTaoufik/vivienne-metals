export const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const euro=n=>new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2}).format(n/100);
export function lineChart(points,series,{label='Historique des prix en euros',height=270}={}) {
  const w=820,h=height,pad={left:63,right:18,top:26,bottom:35};
  const values=points.flatMap(p=>series.map(s=>p[s.key]).filter(v=>Number.isFinite(v)));
  if(!values.length)return '<div class="empty"><h3>Aucune observation disponible</h3><p>Les prix apparaîtront après une collecte réussie.</p></div>';
  let low=Math.min(...values),high=Math.max(...values);const margin=Math.max((high-low)*.2,high*.012,50);low=Math.max(0,low-margin);high+=margin;
  const x=i=>points.length===1?w/2:pad.left+(w-pad.left-pad.right)*i/(points.length-1),y=v=>pad.top+(h-pad.top-pad.bottom)*(1-(v-low)/(high-low));
  let svg=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${escapeHtml(label)}"><title>${escapeHtml(label)}</title><desc>${points.length} observation(s). Les lignes ne constituent pas une prévision.</desc>`;
  for(let i=0;i<5;i++){const value=low+(high-low)*i/4,Y=y(value);svg+=`<line x1="${pad.left}" x2="${w-pad.right}" y1="${Y}" y2="${Y}" stroke="#e8edf1" stroke-dasharray="3 4"/><text x="${pad.left-10}" y="${Y+4}" text-anchor="end" font-size="12" fill="#75818e">${euro(value)}</text>`;}
  for(const s of series){let previous=null;points.forEach((p,i)=>{const v=p[s.key];if(!Number.isFinite(v)){previous=null;return;}const X=x(i),Y=y(v);if(previous)svg+=`<line x1="${previous.x}" y1="${previous.y}" x2="${X}" y2="${Y}" stroke="${s.color}" stroke-width="2.4" ${s.dash?'stroke-dasharray="5 5"':''}/>`;svg+=`<circle cx="${X}" cy="${Y}" r="${points.length<5?4:2.3}" fill="${s.color}" tabindex="0" aria-label="${escapeHtml(p.label)} : ${escapeHtml(s.label)} ${euro(v)} euros"><title>${escapeHtml(p.label)} · ${escapeHtml(s.label)} : ${euro(v)} €</title></circle>`;previous={x:X,y:Y};});}
  const ticks=points.length===1?[0]:[0,Math.floor((points.length-1)/2),points.length-1];
  for(const i of [...new Set(ticks)])svg+=`<text x="${x(i)}" y="${h-9}" text-anchor="middle" font-size="12" fill="#75818e">${escapeHtml(points[i].label)}</text>`;
  return svg+'</svg>';
}
