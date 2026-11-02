from pathlib import Path
import tempfile,unittest,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'tools'))
from download_arcgis import export

class RetrievalTests(unittest.TestCase):
    def fake(self,mode='ok'):
        calls={'counts':0}
        def fetch(url,p):
            if not url.endswith('/query'): return {'objectIdField':'id','fields':[{'name':'id'},{'name':'value'}],'maxRecordCount':2}
            if p.get('returnCountOnly'):
                calls['counts']+=1
                return {'count':6 if mode=='changed' and calls['counts']>1 else 5}
            if p.get('returnIdsOnly'): return {'objectIds':[1,2,3,4,5]}
            ids=list(map(int,p['objectIds'].split(',')))
            if mode=='missing': ids=ids[:-1]
            if mode=='duplicate': ids=[ids[0]]*len(ids)
            return {'features':[{'attributes':{'id':i,'value':None if i==1 else i}} for i in ids], 'exceededTransferLimit':mode=='truncated'}
        return fetch
    def test_complete_and_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'data.csv'
            self.assertTrue(export('https://x/0',['value'],'1=1',out,10,self.fake())['complete'])
            result=export('https://x/0',['value'],'1=1',out,3,self.fake())
            self.assertFalse(result['complete']); self.assertEqual(result['retrieved'],3)
    def test_incomplete_never_written_as_complete(self):
        for mode in ['missing','duplicate','truncated','changed']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as t:
                out=Path(t)/'data.csv'
                with self.assertRaises(RuntimeError): export('https://x/0',['value'],'1=1',out,10,self.fake(mode))
                self.assertFalse(out.exists())
    def test_unknown_field(self):
        with self.assertRaises(ValueError): export('https://x/0',['owner_name'],'1=1',Path('unused.csv'),10,self.fake())
