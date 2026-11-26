"""Rebuild homes.json from the DSHS "Long-Term Care Residential Care" CSV export.
Usage: python3 scripts/build_data.py path/to/export.csv homes.json
"""
from datetime import datetime
import csv, json, re, sys
src, out = sys.argv[1], sys.argv[2]
KEEP_UP = {'AFH','LLC','II','III','IV','ALF','DD','NW','NE','SW','SE','N','S','E','W','PLLC','INC','USA','RN','ICF','MH','A&A','LP'}
def tc(s):
    s = re.sub(r'\s+', ' ', s.replace('"','').strip())
    s = re.sub(r'^[^A-Za-z0-9]+', '', s)
    def w(m):
        t = m.group(0)
        return t if t.upper() in KEEP_UP else t[:1].upper() + t[1:].lower()
    return re.sub(r"[A-Za-z][A-Za-z'&]*", w, s)
SP = {'Dementia':'D','Mental Health':'M','Developmental Disabilities':'X'}
TYPE = {'AF':'A','BH':'L'}
rows = []
latest = None
for r in csv.DictReader(open(src, encoding='utf-8-sig')):
    if r['GDL archive date'].strip() or r['Facility type'] not in TYPE or r['Facility status'] != 'OP':
        continue
    try:
        d = datetime.strptime(r['GDL publish date'].split()[0], '%m/%d/%Y').date()
        latest = d if latest is None or d > latest else latest
    except (ValueError, IndexError):
        pass
    sp = ''.join(SP[s.strip()] for s in r['Specialty'].split(',') if s.strip() in SP)
    try: lat, lon = round(float(r['Latitude']), 5), round(float(r['Longitude']), 5)
    except ValueError: lat = lon = None
    city = r['Corrected postal community'] or r['Location city']
    city = {'Seatac':'SeaTac','SEATAC':'SeaTac'}.get(city, city)
    rows.append([
        r['License number'], TYPE[r['Facility type']], tc(r['Facility name']),
        r['Corrected address'] or tc(r['Location address']), city if city=='SeaTac' else tc(city), r['Corrected ZIP Code'] or r['Location ZIP Code'],
        r['Location county'].strip().title(), r['Telephone'].strip(), int(r['Licensed bed count'] or 0),
        sp, 1 if r['Contract'].strip() else 0, r['Contract'].strip(), lat, lon])
rows.sort(key=lambda x: x[2])
meta = {'asOf': latest.isoformat() if latest else '', 'source': 'Washington DSHS Long-Term Care Residential Care open data', 'fields': ['lic','type','name','addr','city','zip','county','phone','beds','spec','medicaid','contracts','lat','lon']}
json.dump({'meta': meta, 'rows': rows}, open(out, 'w'), separators=(',', ':'))
print(len(rows), sum(1 for x in rows if x[1]=='A'), sum(1 for x in rows if x[1]=='L'))
print(rows[0]); print(rows[len(rows)//2])
