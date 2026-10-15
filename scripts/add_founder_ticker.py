"""Add a public ticker request to both research lists; never execute issue text."""
import json,os,re
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
root=Path(__file__).resolve().parents[1]
event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
match=re.fullmatch(r'Ticker request: ([A-Z][A-Z0-9.\-^]{0,14})',event['issue']['title'])
if not match:raise SystemExit(0)
ticker=match[1]
def read(p):return json.loads((root/p).read_text())
def write(p,s):(root/p).write_text(json.dumps(s,indent=2)+'\n')
r=read('data/founder_filters.json');r['tickers']=sorted(set(r['tickers']+[ticker]))
for f in r['filters']:
 u=urlsplit(f['original_url']);q=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if k!='ticker_symbol']
 f['ticker_urls'][ticker]=urlunsplit(u._replace(query=urlencode(q+[('ticker_symbol',ticker)])))
 f['group_url']=urlunsplit(u._replace(query=urlencode(q+[('ticker_symbol',','.join(r['tickers']))])))
s=read('data/founders.json');s['companies'].setdefault(ticker,{'name':ticker,'ir_url':'','source_urls':[],'event_note':'Requested coverage added. Official company pages and events are being researched.'})
for f in r['filters']:
 if not any(c['ticker']==ticker and c['filter']==f['name'] for c in s['flow_checks']):s['flow_checks'].append({'ticker':ticker,'filter':f['name'],'status':'pending','last_success':None})
b=read('data/snapshot.json');b['watchlist']=sorted(set(b.get('watchlist',[])+[ticker]))
write('data/founder_filters.json',r);write('data/founders.json',s);write('data/snapshot.json',b)
