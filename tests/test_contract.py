import copy
import json
from pathlib import Path
import sys
import unittest
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from download_arcgis import export

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=yaml.safe_load((ROOT/'Code Violations Chatbot Schema.yaml').read_text(encoding='utf-8'))
        cls.meta=json.loads((ROOT/'tests/fixtures/metadata.json').read_text())
    def validator(self,path):
        schema=copy.deepcopy(self.spec['paths'][path]['get']['responses']['200']['content']['application/json']['schema'])
        schema['components']=self.spec['components']
        return Draft202012Validator(schema)
    def test_metadata_and_query_fixtures(self):
        self.validator('/0').validate(self.meta)
        for name in ['sample','count']:
            self.validator('/0/query').validate(json.loads((ROOT/'tests/fixtures'/f'{name}.json').read_text()))
        for fixture in [{'objectIds':[1,2,3]},{'objectIds':None},{'error':{'code':400,'message':'Invalid field','details':[]}},{'features':[]},{'features':[{'attributes':{'violation_date':None,'ObjectId':1,'Latitude':43.1}}]}]:
            self.validator('/0/query').validate(fixture)
    def test_numeric_attributes_are_not_strings(self):
        self.assertFalse(self.validator('/0/query').is_valid({'features':[{'attributes':{'violation_date':'yesterday','ObjectId':'1'}}]}))
    def test_default_fields_exist_and_json_only(self):
        params={p['name']:p['schema'] for p in self.spec['paths']['/0/query']['get']['parameters']}
        self.assertLessEqual(set(params['outFields']['default'].split(',')),{f['name'] for f in self.meta['fields']})
        self.assertEqual(params['f']['enum'],['json'])
        self.assertLessEqual(params['resultRecordCount']['maximum'],self.meta['maxRecordCount'])
    def test_openapi_validation(self):
        from openapi_spec_validator import validate_spec
        validate_spec(self.spec)
    def test_disclaimer_and_feedback_preserved(self):
        original=(ROOT/'tests/fixtures/original-instructions.txt').read_text(encoding='utf-8')
        revised=(ROOT/'Code Violations Chatbot Instructions.txt').read_text(encoding='utf-8')
        disclaimer=original[original.index('Before starting analysis, it starts each conversation'):original.index('When appropriate, ask the user for feedback:')].strip()
        feedback=original[original.index('When appropriate, ask the user for feedback:'):original.index(' Before starting analysis, it checks')].strip()
        self.assertIn(disclaimer,revised); self.assertIn(feedback,revised)
        self.assertLessEqual(len(revised),8000)

if __name__=='__main__': unittest.main()
