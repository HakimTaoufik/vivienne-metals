import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from collector.adapters import parse, money, ParseError, clean_url
from collector.cli import collect, validate
from collector.http import Client, robots_allowed
from collector.store import connect, save, export, previous

ROOT=Path(__file__).resolve().parents[1]
SOURCES=json.loads((ROOT/'config/sources.json').read_text())
STAMP='2026-09-21T14:00:00+00:00'


def source(id):return next(s for s in SOURCES if s['id']==id)
def fixture(id):return (ROOT/'tests/fixtures'/f'{id}.html').read_text()


class MoneyTests(unittest.TestCase):
    def test_french_and_decimal(self):
        for value,expected in [('1\u202f234,56 €',123456),('1\xa0234,56',123456),('1234.56',123456),('699.63001',69963),('0.005',1)]:
            with self.subTest(value=value):self.assertEqual(money(value),expected)
    def test_unavailable(self):
        for value in ['0','0,00 €','—','--','']:
            with self.subTest(value=value):self.assertIsNone(money(value))
    def test_ambiguous_rejected(self):
        for value in ['1,234.56','NaN','Infinity','-3','10 € min. 2','12%','1e3','10000001']:
            with self.subTest(value=value):self.assertRaises(ParseError,money,value)
    def test_urls(self):
        self.assertEqual(clean_url('https://changevivienne.com/a?from_slider=1'),'https://changevivienne.com/a')
        self.assertRaises(ParseError,clean_url,'javascript:alert(1)')


class AdapterTests(unittest.TestCase):
    def test_all_captured_sources(self):
        for s in SOURCES:
            with self.subTest(source=s['id']):
                p=ROOT/'tests/fixtures'/f"{s['id']}.html"
                if not p.exists():continue
                quotes,_=parse(p.read_text(),s,STAMP)
                self.assertGreater(len(quotes),0)
                self.assertTrue(all(q['currency']=='EUR' for q in quotes))
    def test_home_direction_and_quantities(self):
        q,_=parse(fixture('cv-coins'),source('cv-coins'),STAMP)
        coq=next(x for x in q if x['product']=='coq20')
        self.assertEqual((coq['bid'],coq['ask']),(69492,73150))
        silver=next(x for x in q if x['product']=='hercule50')
        self.assertEqual(silver['minBuy'],10)
        self.assertNotIn('gold100', [x['product'] for x in q]) # Combibar is distinct.
    def test_category_customer_direction(self):
        q,s= parse(fixture('cv-gold'),source('cv-gold'),STAMP)
        bar=next(x for x in q if x['product']=='gold1000')
        self.assertEqual((bar['bid'],bar['ask']),(11959358,12410100))
        self.assertAlmostEqual(s[0]['eurPerGram'],122.01842)
    def test_out_of_stock_is_not_an_ask(self):
        q,_=parse(fixture('cv-silver'),source('cv-silver'),STAMP)
        self.assertTrue(all(x['ask'] is None for x in q))
        self.assertEqual(q[0]['bid'],175550)
    def test_joubert_ignores_reference_and_bulk_prices(self):
        q,_=parse(fixture('joubert'),source('joubert'),STAMP)
        coin=next(x for x in q if x['product']=='napoleon20')
        self.assertEqual((coin['bid'],coin['ask']),(69400,73000))
        self.assertIsNone(coin['minSell'])
    def test_or_change_both_pages(self):
        q,_=parse(fixture('oc-coins-bid'),source('oc-coins-bid'),STAMP)
        self.assertEqual(q[0]['bid'],69963);self.assertIsNone(q[0]['ask'])
        q,_=parse(fixture('oc-coins-ask'),source('oc-coins-ask'),STAMP)
        self.assertEqual(q[0]['ask'],73511);self.assertIsNone(q[0]['bid']);self.assertIsNone(q[0]['minBuy'])
    def test_drift_fails_closed(self):
        self.assertRaises(ParseError,parse,fixture('cv-gold').replace('cv-table-row','new-layout'),source('cv-gold'),STAMP)
        self.assertRaises(ParseError,parse,fixture('cv-gold').replace('cv-price-buy','new-price'),source('cv-gold'),STAMP)
    def test_price_inversion_rejected(self):
        self.assertRaises(ParseError,parse,fixture('cv-coins').replace('data-price="731.5"','data-price="100"'),source('cv-coins'),STAMP)
    def test_unknown_direction_rejected(self):
        self.assertRaises(ParseError,parse,fixture('cv-coins').replace('data-action="buy"','data-action="other"'),source('cv-coins'),STAMP)
    def test_quarantine(self):
        q,s=parse(fixture('cv-gold'),source('cv-gold'),STAMP);old={x['product']:copy.deepcopy(x) for x in q}
        q[0]['ask']*=100
        self.assertRaises(ParseError,validate,q,s,old)
    def test_spot_units_sanity(self):
        self.assertRaises(ParseError,validate,[],[{'metal':'gold','eurPerGram':122000}],{})


class StorageTests(unittest.TestCase):
    def test_atomic_idempotent_and_daily_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=connect(tmp+'/market.sqlite');q,s=parse(fixture('cv-gold'),source('cv-gold'),STAMP)
            health={'id':'cv-gold','status':'ok'}
            save(db,q,s,health);save(db,q,s,health)
            self.assertEqual(db.execute('SELECT count(*) FROM observations').fetchone()[0],len(q))
            self.assertEqual(len(previous(db,'cv-gold')),len(q))
            q2=copy.deepcopy(q);q2[0]['observedAt']='2026-09-21T15:00:00+00:00';q2[0]['ask']+=100
            save(db,q2,[],health);out=export(db,tmp+'/market.json','2026-09-21T15:01:00+00:00')
            self.assertEqual(len(out['history']),len(q));self.assertEqual(len(out['intraday']),len(q)+1)
            self.assertTrue(all(x.get('meltCents',0)>0 for x in out['quotes']))
            self.assertEqual(json.loads(Path(tmp+'/market.json').read_text()),out);db.close()
    def test_failed_source_retains_old_observation_and_exposes_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ss=[source('cv-gold')]
            first,n=collect(tmp+'/db',tmp+'/out',ss,lambda _:fixture('cv-gold'))
            second,n=collect(tmp+'/db',tmp+'/out',ss,lambda _:'<html>Unavailable</html>')
            self.assertEqual(n,0);self.assertEqual(first['quotes'],second['quotes'])
            self.assertEqual(second['health'][0]['status'],'error')
    def test_no_future_spot_pairing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=connect(tmp+'/db');q,s=parse(fixture('cv-gold'),source('cv-gold'),STAMP)
            for spot in s:spot['observedAt']='2026-09-21T15:00:00+00:00'
            save(db,q,s,{'id':'cv-gold','status':'ok'});out=export(db,tmp+'/out','2026-09-21T15:01:00+00:00')
            self.assertTrue(all('meltCents' not in x for x in out['quotes']));db.close()


class HttpTests(unittest.TestCase):
    def test_robots_wildcard_and_allow(self):
        r='User-agent: *\nDisallow: /*?\nDisallow: /private/\nAllow: /private/public$'
        self.assertTrue(robots_allowed(r,'/or/lingots'));self.assertFalse(robots_allowed(r,'/or?x=1'))
        self.assertTrue(robots_allowed(r,'/private/public'));self.assertFalse(robots_allowed(r,'/private/public/other'))
    def test_robots_specific_agent(self):
        self.assertFalse(robots_allowed('User-agent: VivienneMetals\nDisallow: /\nUser-agent: *\nAllow: /','/'))
    def test_403_not_retried(self):
        attempts=[]
        def opener(*args,**kwargs):attempts.append(1);raise HTTPError('https://x',403,'Forbidden',{},None)
        self.assertRaises(HTTPError,Client(opener=opener,sleeper=lambda _:None).raw,'https://x')
        self.assertEqual(len(attempts),1)
    def test_transient_502_bounded(self):
        attempts=[]
        def opener(*args,**kwargs):attempts.append(1);raise HTTPError('https://x',502,'Bad Gateway',{},None)
        self.assertRaises(HTTPError,Client(opener=opener,sleeper=lambda _:None).raw,'https://x')
        self.assertEqual(len(attempts),3)


if __name__=='__main__':unittest.main()
