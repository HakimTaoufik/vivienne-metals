// DOM integration checks, not a substitute for the separate real-browser suite.
import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const html=await readFile('web/index.html','utf8');
let sequence=0;
async function app(raw=null){
  const dom=new JSDOM(html,{url:'https://example.github.io/vivienne-metals/',pretendToBeVisual:true});
  const w=dom.window;
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  Object.assign(globalThis,{window:w,document:w.document,localStorage:w.localStorage,FormData:w.FormData,confirm:()=>true});
  if(raw!==null)w.localStorage.setItem('vivienne.portfolio.v1',raw);
  globalThis.fetch=async path=>{try{return {ok:true,json:async()=>JSON.parse(await readFile(resolve('dist',path),'utf8'))};}catch{return {ok:false,status:404}}};
  await import(pathToFileURL(resolve('dist/app.mjs')).href+'?case='+sequence++);
  for(let i=0;i<100&&!w.document.querySelector('#dealer-table table');i++)await new Promise(r=>setTimeout(r,5));
  return {w,dom,$:id=>w.document.getElementById(id)};
}
const submit=(w,form)=>form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
test('DOM: real app renders quotes and switches between metals',async()=>{const {w,dom,$}=await app();assert.match($('dealer-table').textContent,/Change Vivienne/);w.document.querySelector('[data-metal="silver"]').click();assert.equal($('product-select').value,'hercule50');assert.match($('chart-note').textContent,/journée/);assert.ok($('price-chart').querySelector('svg'));dom.window.close();});
test('DOM: buy, reload, oversell and malicious note exercise actual handlers',async()=>{let {w,dom,$}=await app();w.document.querySelector('[data-tab="portfolio"]').click();$('add-transaction').click();let f=$('transaction-form');f.elements.quantity.value='2';f.elements.price.value='600';f.elements.note.value='<img src=x onerror="alert(1)">';submit(w,f);assert.equal($('transaction-dialog').hasAttribute('open'),false);assert.match($('transactions').textContent,/600,00/);assert.equal($('transactions').querySelector('img'),null);const raw=w.localStorage.getItem('vivienne.portfolio.v1');dom.window.close();({w,dom,$}=await app(raw));w.document.querySelector('[data-tab="portfolio"]').click();assert.match($('holdings').textContent,/1\s200,00/);$('add-transaction').click();f=$('transaction-form');f.elements.type.value='sell';f.elements.quantity.value='3';f.elements.price.value='700';submit(w,f);assert.match($('transaction-error').textContent,/supérieure au stock/);assert.equal(JSON.parse(w.localStorage.getItem('vivienne.portfolio.v1')).transactions.length,1);dom.window.close();});
test('DOM: corrupt storage stays intact and recording is locked',async()=>{const {w,dom,$}=await app('CORRUPT');assert.match($('global-error').textContent,/illisible/);w.document.querySelector('[data-tab="portfolio"]').click();assert.equal($('add-transaction').disabled,true);assert.equal(w.localStorage.getItem('vivienne.portfolio.v1'),'CORRUPT');dom.window.close();});
test('DOM: settings validate and persist through the real form',async()=>{const {w,dom,$}=await app();w.document.querySelector('[data-tab="settings"]').click();const f=$('settings-form');f.elements.minDays.value='45';f.elements.budgetCents.value='1234.56';submit(w,f);const saved=JSON.parse(w.localStorage.getItem('vivienne.settings.v1'));assert.equal(saved.minDays,45);assert.equal(saved.budgetCents,123456);f.elements.minDays.value='999';submit(w,f);assert.equal(JSON.parse(w.localStorage.getItem('vivienne.settings.v1')).minDays,45);dom.window.close();});
test('DOM: backtest shows cold start rather than a fabricated return',async()=>{const {w,dom,$}=await app();w.document.querySelector('[data-tab="signals"]').click();$('run-backtest').click();assert.match($('backtest-result').textContent,/journée.*disponible/);assert.ok(!$('backtest-result').textContent.includes('100 %'));dom.window.close();});
