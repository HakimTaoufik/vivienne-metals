"""Dealer-specific parsers for public tables and their public embedded price feeds."""
from datetime import datetime
from html import unescape
import json
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
from .dom import Tree


def parse_expanded(body, source, observed):
    # Imported at call-time to keep the original adapters' public API stable.
    from .adapters import base, money, norm, NAMES, first, positive_int, ParseError, direct_price
    root=Tree(body).root
    quotes=[]
    adapter=source['adapter']
    def new(name,url=None):
        product=NAMES.get(norm(name))
        if not product:return None
        q=base(source,product,url or source['url'],observed)
        q['sideScope']=source.get('side','both')
        if source.get('confirmationRequired'):q['confirmationRequired']=source['confirmationRequired']
        return q
    def append(q):
        if q is not None:quotes.append(q)
    if adapter in ('ydp','vmp'):
        if adapter=='ydp':
            m=re.fullmatch(r'\s*jsonp_callback\((.*)\);?\s*',body,re.S)
            if not m:raise ParseError('Expected public YDP JSONP envelope')
            data=json.loads(m[1]); rows=data['data']['scroll']
            stamp=datetime.strptime(data['config']['timestamp'],'%Y%m%d%H%M%S')
        else:
            m=re.search(r'\bvar\s+orpDataCarousel\s*=\s*(\{.*?\});',body,re.S)
            if not m:raise ParseError('VMP public carousel data missing')
            data=json.loads(m[1]);rows=data['produits']
            stamp=datetime.strptime(data['date_extraction'],'%Y-%m-%d %H:%M:%S')
        published=stamp.replace(tzinfo=ZoneInfo('Europe/Paris')).isoformat(timespec='seconds')
        for row in rows:
            q=new(row['libelle'])
            if q is None:continue
            q.update(bid=money(unescape(str(row['achat_cours']))),ask=money(unescape(str(row['vente_cours']))),publishedAt=published)
            q['priceNote']='Quantité, état et stock à confirmer en boutique'
            append(q)
    elif adapter=='merson':
        for row in root.find('article',cls='product-miniature'):
            names=row.find(itemprop='name')
            if len(names)!=1:raise ParseError('Merson product name missing')
            links=names[0].find('a')
            q=new(names[0].text(),links[0].attrs['href'] if links else None)
            if q is None:continue
            price=first(row,'product-price')
            value=money(price.text())
            if value!=money(price.attrs.get('content','')):raise ParseError('Merson visible/structured price mismatch')
            side=source['side'];q[side]=value
            if side=='ask':
                stock=norm(row.text())
                if 'rupture de stock' in stock:q.update(ask=None,availability='unavailable')
                elif 'en stock' in stock:q['availability']='in_stock'
                if "pas de quantite minimum d'achat" in stock:q['minBuy']=1
            else:q['priceNote']='Rachat brut avant fiscalité ; quantité à confirmer'
            append(q)
    elif adapter=='godot':
        tables=root.find('table',cls='cours-cpr-table')
        for table in tables:
            heads=[norm(h.text()) for h in table.find('th')]
            silver=source.get('metal')=='silver'
            if len(heads)!=(6 if silver else 9) or heads[-2:]!=(['achat','vente'] if silver else ['vous achetez','vous vendez']):
                raise ParseError('Godot price column labels changed')
            for row in table.find('tr',cls='cours-cpr-table-row'):
                td=row.find('td')
                if len(td)!=len(heads):raise ParseError('Godot column count changed')
                link=td[1].find('a')[0]
                q=new(td[1].text(),urljoin(source['url'],link.attrs['href']))
                if q is None or q['product'] in source.get('exclude',[]):continue
                for side,cell in [('ask',td[-2]),('bid',td[-1])]:
                    p=first(cell,'cours-cpr-action-btn__price')
                    q[side]=direct_price(p) # crossed-out promotion/reference price excluded
                append(q)
    elif adapter=='godot_product':
        q=base(source,source['product'],source['url'],observed);q['sideScope']='both'
        tables=root.find('table',cls='produitVolumes')
        buy=[t for t in tables if 'VOUS ACHETEZ' in t.text()]
        sell=[t for t in tables if 'VOUS VENDEZ' in t.text()]
        if len(buy)!=1 or len(sell)!=1:raise ParseError('Godot labeled volume tables missing')
        tiers=[];minimum=1
        for row in buy[0].find('tr'):
            cells=row.find('td',cls='JQpa')
            if not cells:continue
            cell=cells[0];maximum=positive_int(cell.attrs['data-valmax'])
            visible=[s for s in cell.find('span') if re.fullmatch(r'pa\d+',s.attrs.get('id',''))]
            if len(visible)!=1:raise ParseError('Godot visible unit price missing')
            tiers.append(dict(min=minimum,max=maximum,price=money(visible[0].text())));minimum=maximum+1
        terminal=buy[0].find('span',id='paA')
        if len(terminal)!=1:raise ParseError('Godot terminal volume band missing')
        tiers.append(dict(min=minimum,max=None,price=money(terminal[0].text())))
        if not tiers:raise ParseError('Godot tiers missing')
        controls=root.find('input',id='achQte')
        q.update(ask=tiers[0]['price'],askTiers=tiers,minBuy=positive_int(controls[0].attrs['min']),maxBuy=positive_int(controls[0].attrs['max']))
        bids=sell[0].find('span',id='pv')
        if len(bids)!=1:raise ParseError('Godot buyback quote missing')
        q.update(bid=money(bids[0].text()),minSell=1,priceNote='Prix d’achat net ; rachat brut avant fiscalité')
        append(q)
    elif adapter=='arcades':
        table=root.find('table',id='gold_table')
        if len(table)!=1 or [h.text() for h in table[0].find('th')][-2:]!=['Achat','Vente']:raise ParseError('Arcades labels changed')
        for row in table[0].find('tr'):
            names=row.find(cls='product_name')
            if not names:continue
            q=new(names[0].text())
            if q is None:continue
            q.update(bid=money(first(row,'product_buy').text()),ask=money(first(row,'product_sell').text()))
            append(q)
    elif adapter=='abacor':
        for row in root.find('li',cls='product'):
            names=row.find('h2',cls='woocommerce-loop-product__title')
            if len(names)!=1:raise ParseError('Abacor product heading missing')
            links=row.find('a',cls='woocommerce-LoopProduct-link')
            q=new(names[0].text(),links[0].attrs['href'] if links else None)
            if q is None:continue
            price=first(row,'price')
            # This site's price formatter uses US grouping; require its exact grammar.
            text=price.text().replace('€','').strip()
            if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)\.\d{2}',text):raise ParseError('Abacor price format changed')
            q['ask']=money(text.replace(',',''))
            if 'outofstock' in row.attrs.get('class','').split():q.update(ask=None,availability='unavailable')
            else:
                buttons=row.find('a',cls='add_to_cart_button')
                if len(buttons)==1 and buttons[0].attrs.get('data-quantity')=='1':q.update(minBuy=1,availability='in_stock')
            q['sideScope']='ask';append(q)
    elif adapter=='ccopera':
        tables=[t for t in root.find('table',cls='metal') if any(term in norm(' '.join(h.text() for h in t.find('th'))) for term in ('gre a gre','p.u. net','cco achete'))]
        if len(tables)!=1:raise ParseError('CCO main table missing')
        table=tables[0];head=norm(' '.join(t.text() for t in table.find('th')));side=source['side']
        if side=='bid' and 'cco achete' not in head:raise ParseError('CCO buyback label changed')
        if side=='ask' and not ('gre a gre' in head or 'p.u. net' in head):raise ParseError('CCO net ask label changed')
        for row in table.find('tr'):
            cells=row.find('td')
            if not cells:continue
            links=cells[0].find('a')
            if not links:continue
            names=links[0].find(cls='libelle_standard')
            if len(names)!=1:raise ParseError('CCO standard product name missing')
            q=new(names[0].text(),urljoin(source['url'],links[0].attrs['href']))
            if q is None:continue
            if side=='ask':
                prices=row.find('span',itemprop='price')
                if len(prices)>1:raise ParseError('Multiple CCO unit prices')
                q['ask']=money(prices[0].text()) if prices else None
                if 'pas de vente' in norm(row.text()):q.update(ask=None,availability='unavailable')
            else:
                if len(cells)!=7:raise ParseError('CCO buyback column count changed')
                q['bid']=money(cells[5].text())
            minimum=re.search(r'Qte min\.\s*:?\s*(\d+)',norm(cells[-1].text()),re.I)
            if minimum:q['minBuy' if side=='ask' else 'minSell']=positive_int(minimum[1])
            q['priceNote']='Gré à gré ; état et disponibilité à confirmer'
            append(q)
    elif adapter=='goldunion_product':
        candidates=[]
        for script in root.find('script',type='application/ld+json'):
            data=json.loads(script.text())
            if isinstance(data,dict) and data.get('@type')=='Product':candidates.append(data)
        if not candidates:raise ParseError('GoldUnion Product JSON-LD missing')
        values=[]
        for product in candidates:
            offers=product.get('offers',[]);offers=offers if isinstance(offers,list) else [offers]
            if len(offers)!=1:raise ParseError('GoldUnion ambiguous variants')
            offer=offers[0]
            if offer.get('priceCurrency')!='EUR':raise ParseError('Non-EUR offer')
            values.append((money(offer['price']),offer.get('availability','').replace('http://','https://')))
        if len(set(values))!=1:raise ParseError('GoldUnion conflicting structured prices')
        q=base(source,source['product'],source['url'],observed);q['sideScope']='ask'
        q.update(ask=values[0][0],minBuy=1,maxBuy=49,priceNote='Prix unitaire pour 1–49 pièces ; remises de volume non extrapolées')
        if values[0][1].endswith('/OutOfStock'):q.update(ask=None,availability='unavailable')
        elif values[0][1].endswith('/InStock'):q['availability']='in_stock'
        else:raise ParseError('GoldUnion availability unknown')
        append(q)
    else:raise ParseError('Unknown adapter')
    return quotes,[]
