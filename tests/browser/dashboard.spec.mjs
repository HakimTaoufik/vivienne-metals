import {test,expect} from '@playwright/test';

test('dashboard loads, changes metal, and has no horizontal overflow',async({page})=>{
  const errors=[];page.on('pageerror',err=>errors.push(err.message));
  await page.goto('/');await expect(page.getByRole('heading',{name:'Le marché, en un regard.'})).toBeVisible();
  await expect(page.locator('#dealer-table')).toContainText('Change Vivienne');
  await page.getByRole('button',{name:'Argent',exact:true}).click();
  await expect(page.locator('#product-select')).toHaveValue('hercule50');
  await expect(page.locator('#chart-note')).not.toBeEmpty();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
test('purchase persists across reload and oversell is blocked',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Mes avoirs',exact:true}).click();
  await page.getByRole('button',{name:'Ajouter une opération',exact:false}).click();
  await page.getByLabel('Quantité',{exact:true}).fill('2');
  await page.getByLabel('Prix payé / reçu par unité (€)').fill('600');
  await page.getByRole('button',{name:'Enregistrer l’opération'}).click();
  await expect(page.locator('#transactions')).toContainText('600,00');
  await page.reload();await page.getByRole('button',{name:'Mes avoirs',exact:true}).click();
  await expect(page.locator('#holdings')).toContainText('1 200,00');
  await page.getByRole('button',{name:'Ajouter une opération',exact:false}).click();
  await page.getByLabel('Opération',{exact:true}).selectOption('sell');
  await page.getByLabel('Quantité',{exact:true}).fill('3');
  await page.getByLabel('Prix payé / reçu par unité (€)').fill('700');
  await page.getByRole('button',{name:'Enregistrer l’opération'}).click();
  await expect(page.locator('#transaction-error')).toContainText('supérieure au stock');
});
test('settings save locally and signal warm-up is honest',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Paramètres',exact:true}).click();
  await page.getByLabel('Minimum de jours distincts',{exact:false}).fill('45');
  await page.getByRole('button',{name:'Enregistrer dans ce navigateur'}).click();
  await page.reload();await page.getByRole('button',{name:'Paramètres',exact:true}).click();
  await expect(page.getByLabel('Minimum de jours distincts',{exact:false})).toHaveValue('45');
  await page.getByRole('button',{name:'Opportunités',exact:true}).click();
  await expect(page.locator('#signal-status')).not.toBeEmpty();
  await page.getByRole('button',{name:'Lancer le backtest'}).click();
  await expect(page.locator('#backtest-result')).not.toBeEmpty();
});
test('corrupt backup is preserved and edits are blocked',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('vivienne.portfolio.v1','BROKEN_BACKUP'));
  await page.goto('/');await expect(page.locator('#global-error')).toContainText('illisible');
  await page.getByRole('button',{name:'Mes avoirs',exact:true}).click();
  await expect(page.getByRole('button',{name:'Ajouter une opération',exact:false})).toBeDisabled();
  expect(await page.evaluate(()=>localStorage.getItem('vivienne.portfolio.v1'))).toBe('BROKEN_BACKUP');
});
test('backup export and import restore a validated transaction',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Mes avoirs',exact:true}).click();
  const tx={id:'browser-test',product:'coq20',type:'buy',quantity:1,unitPriceCents:50000,feesCents:0,date:'2026-01-01',note:'Test de restauration'};
  await page.locator('#backup-file').setInputFiles({name:'backup.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify({schemaVersion:1,transactions:[tx]}))});
  await expect(page.locator('#transactions')).toContainText('Test de restauration');
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Exporter la sauvegarde'}).click();
  expect((await download).suggestedFilename()).toContain('vivienne-sauvegarde');
});
test('expanded coverage, geographic filter and quantity comparison',async({page})=>{
  await page.goto('/');await expect(page.locator('.shop-card')).toHaveCount(12);
  await expect(page.locator('#coverage-count')).toContainText('8 rue Vivienne');
  await page.getByLabel('Produit suivi').selectOption('napoleon20');
  await page.getByRole('button',{name:'Rue Vivienne',exact:true}).click();
  await expect(page.locator('#dealer-table [data-dealer="ccopera"]')).toHaveCount(0);
  await page.getByLabel('Boutique comparée').selectOption('godot');
  await page.getByLabel('Quantité à comparer').fill('10');
  await page.getByLabel('Quantité à comparer').press('Tab');
  await expect(page.locator('#dealer-table tbody tr')).toHaveCount(1);
  await expect(page.locator('#comparison-context')).toContainText('10 unité(s)');
  await expect(page.locator('#freshness-note')).toContainText('ne lance pas une collecte');
});
test('offline replay displays captured unit price and changes Godot volume band',async({page})=>{
  await page.goto('/demo.html');await expect(page.getByText('Démonstration locale · relevé réel',{exact:false})).toBeVisible();
  await page.getByLabel('Produit suivi').selectOption('napoleon20');
  await page.getByLabel('Boutique comparée').selectOption('godot');
  const snapshot=await (await page.request.get('/data/market.json')).json();
  const quote=snapshot.quotes.find(q=>q.source==='godot-napoleon');
  const euro=n=>new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(n/100);
  await expect(page.locator('#best-ask')).toHaveText(euro(quote.ask));
  await page.getByLabel('Quantité à comparer').fill('10');await page.getByLabel('Quantité à comparer').press('Tab');
  await expect(page.locator('#best-ask')).toHaveText(euro(quote.askTiers.find(t=>t.min===10).price));
});
