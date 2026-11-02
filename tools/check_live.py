"""Read-only contract smoke check; never changes the GPT or ArcGIS source."""
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen
import yaml
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
spec=yaml.safe_load((ROOT/'Code Violations Chatbot Schema.yaml').read_text(encoding='utf-8'))
base=spec['servers'][0]['url']
def check(path,params):
    with urlopen(base+path+'?'+urlencode(params),timeout=40) as response: data=json.load(response)
    if data.get('error'): raise RuntimeError(data['error'])
    schema=dict(spec['paths'][path]['get']['responses']['200']['content']['application/json']['schema'],components=spec['components'])
    Draft202012Validator(schema).validate(data)
    return data
meta=check('/0',{'f':'json'})
params={p['name']:p['schema'] for p in spec['paths']['/0/query']['get']['parameters']}
assert set(params['outFields']['default'].split(',')) <= {f['name'] for f in meta['fields']}
count=check('/0/query',{'f':'json','where':'1=1','returnCountOnly':'true'})
sample=check('/0/query',{'f':'json','where':'1=1','outFields':meta['objectIdField']+',violation_date,status_type_name','returnGeometry':'false','orderByFields':meta['objectIdField']+' ASC','resultRecordCount':2})
print(json.dumps({'fields':len(meta['fields']),'count':count['count'],'sample_rows':len(sample['features']),'sample_truncated':sample.get('exceededTransferLimit',False)}))
