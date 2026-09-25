import json
import tempfile
import unittest
from pathlib import Path
from collector.store import connect, save, merge_snapshot, export

class SnapshotRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=connect(Path(self.tmp.name)/'market.sqlite')
  self.old={'source':'ccopera-coins-ask','dealer':'ccopera','product':'napoleon20','observedAt':'2026-09-24T08:52:52+00:00','ask':72400,'bid':None,'minBuy':1,'minSell':None,'currency':'EUR'}
  self.health={'id':'ccopera-coins-ask','dealer':'ccopera','status':'ok','checkedAt':self.old['observedAt']}
  self.snapshot={'history':[self.old],'quotes':[self.old],'health':[self.health]}
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def test_new_dealer_capture_merges_into_existing_archive_without_refreshing_time(self):
  other={**self.old,'source':'other','dealer':'other'}
  save(self.db,[other],[],{'id':'other','status':'ok'})
  merge_snapshot(self.db,self.snapshot);merge_snapshot(self.db,self.snapshot)
  out=export(self.db,Path(self.tmp.name)/'market.json','2026-09-25T16:00:00+00:00')
  self.assertEqual(len(out['quotes']),2)
  recovered=next(q for q in out['quotes'] if q['dealer']=='ccopera')
  self.assertEqual(recovered['observedAt'],self.old['observedAt'])
  self.assertEqual(recovered['ask'],72400)
 def test_current_failure_status_survives_archive_replay(self):
  failed={**self.health,'status':'error','checkedAt':'2026-09-25T15:00:00+00:00','error':'HTTP 403'}
  save(self.db,[],[],failed);merge_snapshot(self.db,self.snapshot)
  actual=json.loads(self.db.execute('SELECT payload FROM health WHERE source=?',(failed['id'],)).fetchone()[0])
  self.assertEqual(actual,failed)
