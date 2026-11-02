"""Read-only, bounded ArcGIS CSV download with a completeness receipt.

python download_arcgis.py LAYER_URL --fields field1,field2 --output data.csv
The output is a snapshot, not a promise that a live layer stayed unchanged.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def request(url, params):
    for attempt in range(3):
        try:
            with urlopen(Request(url + '?' + urlencode(params), headers={'User-Agent':'DataCuse-read-only-export/1.0'}), timeout=40) as response:
                data = json.load(response)
            if data.get('error'):
                raise RuntimeError('ArcGIS error: ' + json.dumps(data['error']))
            return data
        except HTTPError as exc:
            if exc.code in (429, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise

def export(url, fields, where, output, maximum=10000, fetch=request):
    if maximum < 1:
        raise ValueError('max-rows must be positive')
    url = url.rstrip('/')
    meta = fetch(url, {'f':'json'})
    oid = meta.get('objectIdField')
    known = {f['name'] for f in meta.get('fields', [])}
    if not oid or oid not in known:
        raise ValueError('No usable object ID field')
    fields = list(dict.fromkeys([oid] + (fields or list(known))))
    if any(f not in known for f in fields):
        raise ValueError('Requested field absent from current metadata')
    query = url + '/query'
    base = {'f':'json', 'where':where}
    count = fetch(query, dict(base, returnCountOnly='true')).get('count')
    id_response = fetch(query, dict(base, returnIdsOnly='true'))
    ids = sorted(id_response.get('objectIds') or [])
    if count is None or len(ids) != count or len(set(ids)) != len(ids) or id_response.get('exceededTransferLimit'):
        raise RuntimeError('ID inventory is incomplete or changed; no complete export is possible')
    wanted = ids[:maximum]
    batch_size = min(200, meta.get('maxRecordCount') or 200)
    rows, seen = [], set()
    for start in range(0, len(wanted), batch_size):
        batch = wanted[start:start+batch_size]
        data = fetch(query, dict(base, objectIds=','.join(map(str,batch)), outFields=','.join(fields), returnGeometry='false'))
        features = data.get('features')
        if features is None or data.get('exceededTransferLimit'):
            raise RuntimeError('Truncated or malformed batch; export not written')
        attributes = [f['attributes'] for f in features]
        returned = [r.get(oid) for r in attributes]
        if set(returned) != set(batch) or len(returned) != len(set(returned)) or seen.intersection(returned):
            raise RuntimeError('Missing or duplicated IDs; source may have changed')
        seen.update(returned)
        rows.extend(attributes)
    after = fetch(query, dict(base, returnCountOnly='true')).get('count')
    if after != count:
        raise RuntimeError('Count changed during retrieval; export not written')
    rows.sort(key=lambda r:r[oid])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    receipt = {'source':url,'where':where,'checked_at':datetime.now(timezone.utc).isoformat(),'expected':count,'retrieved':len(rows),'complete':len(rows)==count,'bounded_at':maximum,'note':'IDs and counts verified before/after; concurrent updates to values can still occur. CSV empty cells represent JSON null or absent attributes, not zero.'}
    output.with_suffix('.receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('url')
    p.add_argument('--fields', default='')
    p.add_argument('--where', default='1=1')
    p.add_argument('--output', type=Path, default=Path('data.csv'))
    p.add_argument('--max-rows', type=int, default=10000)
    a = p.parse_args()
    print(json.dumps(export(a.url,a.fields.split(',') if a.fields else [],a.where,a.output,a.max_rows),indent=2))
