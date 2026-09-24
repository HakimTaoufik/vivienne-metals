"""Regression checks against captured dealer pages, never generated market history."""
import json,hashlib,re,unittest
from pathlib import Path
from collector.adapters import parse,ParseError
ROOT=Path(__file__).resolve().parents[1]
SOURCES={s['id']:s for s in json.loads((ROOT/'config/sources.json').read_text())}
AT='2026-09-23T14:00:00+00:00'
def body(id):return (ROOT/'tests/fixtures'/f'{id}.html').read_text()
def quotes(id,html=None):return parse(body(id) if html is None else html,SOURCES[id],AT)[0]
def quote(id,product):return next(q for q in quotes(id) if q['product']==product)

class ExpansionTests(unittest.TestCase):
 def test_provenance_hashes(self):
  for f in json.loads((ROOT/'tests/fixtures/expansion-manifest.json').read_text()):
   with self.subTest(f=f['source']):self.assertEqual(hashlib.sha256(body(f['source']).encode()).hexdigest(),f['fixtureSha256'])
 def test_all_12_dealers_and_62_products_have_captured_quotes(self):
  qs=[q for s in SOURCES for q in quotes(s)]
  self.assertEqual(len({q['dealer'] for q in qs}),12)
  self.assertEqual({q['product'] for q in qs},{p['id'] for p in json.loads((ROOT/'config/products.json').read_text())})
 def test_merson_two_directions_and_minimum(self):
  a,b=quote('merson-gold-ask','coq20'),quote('merson-gold-bid','coq20')
  self.assertEqual((a['ask'],a['bid'],a['minBuy']),(72380,None,1))
  self.assertEqual((b['ask'],b['bid'],b['minSell']),(None,69093,None))
 def test_merson_stock_and_structured_mismatch(self):
  q=quotes('merson-gold-ask',body('merson-gold-ask').replace('En stock','Ce produit est actuellement en rupture de stock'))
  self.assertIsNone(next(v for v in q if v['product']=='coq20')['ask'])
  self.assertRaises(ParseError,quotes,'merson-gold-ask',body('merson-gold-ask').replace('content="757.85"','content="1.00"'))
 def test_godot_does_not_use_london_or_fixing(self):
  q=quote('godot-gold','gold1000')
  self.assertEqual((q['ask'],q['bid']),(12341700,11941600))
  self.assertIsNone(q['minBuy'])
 def test_godot_promotion_does_not_use_crossed_out_price(self):
  self.assertEqual(quote('godot-silver','silver1000')['ask'],220000)
  self.assertEqual(quote('godot-silver','hercule10')['ask'],4700)
 def test_godot_actual_volume_bands(self):
  q=quote('godot-napoleon','napoleon20')
  self.assertEqual([t['price'] for t in q['askTiers']],[72600,72500,72450,72300,72150])
  self.assertEqual([t['min'] for t in q['askTiers']],[1,10,50,100,500])
  self.assertEqual((q['minBuy'],q['maxBuy'],q['minSell']),(1,1000,1))
 def test_godot_changed_direction_fails_closed(self):
  self.assertRaises(ParseError,quotes,'godot-gold',body('godot-gold').replace('Vous achetez','Cours'))
 def test_vmp_carousel_direction_and_published_timestamp(self):
  q=quote('vivienne-mp','napoleon20')
  self.assertEqual((q['bid'],q['ask']),(69862,74264))
  self.assertEqual(q['publishedAt'],'2026-09-23T09:10:34+02:00')
 def test_yoda_public_feed_not_reference(self):
  q=quote('bourse','napoleon20')
  self.assertEqual((q['bid'],q['ask']),(68612,73890))
  self.assertEqual(q['publishedAt'],'2026-09-23T13:30:01+02:00')
  self.assertEqual(q['url'],'https://comptoir-or-bourse.fr/cours-boutique')
 def test_yoda_never_evaluates_javascript(self):
  self.assertRaises(ParseError,quotes,'bourse','arbitrary('+body('bourse')+')')
 def test_argentor_warning_is_preserved(self):
  self.assertTrue(quote('argentor','napoleon20')['confirmationRequired'])
 def test_arcades_dealer_direction(self):
  q=quote('arcades','napoleon20');self.assertEqual((q['bid'],q['ask']),(66720,73817))
 def test_abacor_grouping_and_distinct_american_types(self):
  self.assertEqual(quote('abacor-bars','gold1000')['ask'],12400000)
  self.assertEqual(quote('abacor-gold','usd10liberty')['ask'],206000)
  self.assertEqual(quote('abacor-gold','usd10indian')['ask'],222700)
  self.assertIsNone(quote('abacor-gold','coq20')['bid'])
 def test_ccopera_unit_net_and_buyback_not_fixing(self):
  a,b=quote('ccopera-coins-ask','napoleon20'),quote('ccopera-coins-bid','napoleon20')
  self.assertEqual((a['ask'],b['bid'],a['minBuy'],b['minSell']),(72800,68260,1,1))
  self.assertIsNone(quote('ccopera-coins-ask','usd20')['ask'])
 def test_ccopera_silver_unavailable_and_lot_minimum(self):
  self.assertEqual(quote('ccopera-silver-ask','semeuse050')['minBuy'],20)
  self.assertIsNone(quote('ccopera-silver-ask','semeuse2')['ask'])
 def test_goldunion_unit_offer_not_discount(self):
  q=quote('goldunion-coq','coq20');self.assertEqual((q['ask'],q['minBuy'],q['maxBuy']),(76800,1,49))
 def test_goldunion_conflicting_quotes_fail_closed(self):
  changed=re.sub(r'("price"\s*:\s*)768\.0',r'\g<1>123.0',body('goldunion-coq'))
  self.assertRaises(ParseError,quotes,'goldunion-coq',changed)
 def test_joubert_popular_coins_are_mapped_without_packs(self):
  q=quotes('joubert');self.assertEqual(len(q),32);self.assertIn('britanniagold',{x['product'] for x in q});self.assertNotIn('22239',{x['product'] for x in q})
class ContentNegotiationTests(unittest.TestCase):
 def test_html_and_public_jsonp_request_the_right_representation(self):
  from collector.http import Client
  from unittest.mock import MagicMock
  opener=MagicMock()
  response=opener.return_value.__enter__.return_value
  response.read.return_value=b'example'
  for url,expected in [('https://example.org/catalog','text/html,text/plain'),('https://example.org/feed/data.js','application/javascript,application/json,*/*')]:
   response.url=url
   Client(opener=opener).raw(url)
   self.assertEqual(opener.call_args.args[0].get_header('Accept'),expected)
if __name__=='__main__':unittest.main()
