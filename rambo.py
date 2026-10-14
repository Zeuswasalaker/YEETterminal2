"""CSV normalization and exact event/contract matching. No proprietary signals."""
import io
import hashlib
import json
from datetime import date
import pandas as pd

KEY = ['date','time','option_chain_id','side','size','premium']

def filter_name(name):
    for token, label in [('FARCRY','FARCRY ULTRA'),('BAT','BAT'),('Freelance','Freelance Ultra'),('PSU','PSU'),('_WF','WF')]:
        if token.lower() in name.lower(): return label
    return 'T' if '_false_T' in name or '_fal (' in name else 'Other'

def normalize(files):
    frames, warnings = [], []
    for name, content in files:
        try:
            df = pd.read_csv(io.BytesIO(content))
            needed = {'underlying_symbol','expiry','premium','strike','type','date','time','side','size'}
            missing = needed - set(df.columns)
            if missing: raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
            df['underlying_symbol'] = df.underlying_symbol.astype(str).str.strip().str.upper()
            df['expiry'] = pd.to_datetime(df.expiry, errors='coerce').dt.strftime('%Y-%m-%d')
            df['date'] = pd.to_datetime(df.date, errors='coerce').dt.strftime('%Y-%m-%d')
            df['type'] = df.type.astype(str).str.upper()
            df['side'] = df.side.astype(str).str.upper()
            for col in ['premium','strike','size','open_interest','volume']:
                if col not in df: df[col] = None
                df[col] = pd.to_numeric(df[col],errors='coerce')
            if 'option_chain_id' not in df:
                df['option_chain_id'] = df.underlying_symbol + df.expiry.fillna('') + df.type + df.strike.astype(str)
            if 'canceled' in df:
                df = df[~df.canceled.astype(str).str.lower().isin(['true','1'])]
            bad = df[['expiry','date','premium','strike','size']].isna().any(axis=1)
            if bad.sum(): warnings.append(f'{name}: skipped {bad.sum()} invalid rows.')
            df = df[~bad].copy()
            df['filter'] = filter_name(name)
            df['source_file'] = name
            df['record_id'] = df.apply(lambda r: hashlib.sha256(json.dumps([str(r[k]) for k in KEY]).encode()).hexdigest(),axis=1)
            frames.append(df)
        except Exception as exc:
            warnings.append(f'{name}: {exc}')
    if not frames: return [], warnings
    all_rows = pd.concat(frames,ignore_index=True)
    sources = all_rows.groupby('record_id')['filter'].agg(lambda x: ', '.join(sorted(set(x))))
    out = all_rows.drop_duplicates('record_id').copy()
    out['filters'] = out.record_id.map(sources)
    cols = list(dict.fromkeys(KEY + ['record_id','underlying_symbol','expiry','strike','type','filters','source_file','open_interest','volume','next_earnings_date','is_agg','report_flags']))
    out = out[[c for c in cols if c in out]]
    return json.loads(out.to_json(orient='records')), warnings

def match(events, prints, as_of=None):
    as_of = as_of or date.today().isoformat()
    results = []
    for event in events:
        if event.get('status') != 'Confirmed' or event.get('earnings_related',False): continue
        if event['end_date'] < as_of: continue
        rows = [p for p in prints if p['underlying_symbol'] == event['ticker'] and p['date'] <= event['end_date'] and p['expiry'] >= event['end_date']]
        if not rows: continue
        calls = sum(p['premium'] for p in rows if p['type']=='C' and p['side']=='ASK')
        puts = sum(p['premium'] for p in rows if p['type']=='P' and p['side']=='ASK')
        direction = 'Mixed' if calls and puts else 'Call-side' if calls else 'Put-side' if puts else 'Unclear'
        results.append(dict(event, prints=rows, direction=direction, days_until=(date.fromisoformat(event['date'])-date.fromisoformat(as_of)).days, contracts=len(set(p['option_chain_id'] for p in rows))))
    return sorted(results,key=lambda r:(r['date'],r['ticker']))
