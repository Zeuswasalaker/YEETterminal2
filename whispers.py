"""Research leads from the supplied RAMBO screens."""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import streamlit as st

DATA = Path(__file__).parent / 'data'
CAP_LIMIT = 20_000_000_000
MIN_DTE = 7

def load(name):
    try:
        return json.loads((DATA / name).read_text())
    except (OSError, ValueError):
        return {}

def distinct_orders(orders):
    """Treat nearby copies of the same economic print as one observation."""
    accepted = []
    seen_ids = set()
    times = {}
    for p in sorted(orders, key=lambda p: (p.get('date',''),p.get('time',''))):
        record_id = p.get('record_id')
        if record_id and record_id in seen_ids:
            continue
        if record_id:
            seen_ids.add(record_id)
        key = (p.get('date'), p['type'].lower()[0], p.get('strike'), p.get('expiry'), p.get('size'), p.get('premium'))
        try:
            t = datetime.strptime(p.get('time',''), '%H:%M:%S')
        except ValueError:
            # No timestamp to establish an independent print.
            t = None
        prior = times.get(key, [])
        if prior and (t is None or any(a is None or abs((t-a).total_seconds()) <= 60 for a in prior)):
            continue
        times.setdefault(key, []).append(t)
        accepted.append(p)
    return accepted

def leads(prints, caps, events, day, today, min_dte=MIN_DTE, pending=False):
    cutoff = (date.fromisoformat(today) + timedelta(days=min_dte)).isoformat()
    grouped = {}
    for p in prints:
        if not p.get('date') or (day and p['date'] != day) or p['date'] > today or p.get('side') != 'ASK':
            continue
        ticker = p.get('underlying_symbol')
        kind = str(p.get('type', '')).lower()[:1]
        if kind in ('c','p') and ((ticker not in caps) if pending else 0 < caps.get(ticker,0) <= CAP_LIMIT):
            grouped.setdefault(ticker, []).append(p)
    result = []
    for ticker, orders in grouped.items():
        if len({p['type'].lower()[0] for p in orders}) != 1:
            continue
        active = distinct_orders([p for p in orders if p.get('expiry','') >= cutoff])
        if len(active) < 2:
            continue
        linked = [e for e in events if e.get('ticker') == ticker and e.get('status') == 'Confirmed'
                  and not e.get('earnings_related') and 'corporate action' not in e.get('category','').lower()
                  and any(max(today,p['date']) <= e.get('date','') <= p['expiry'] for p in active)]
        result.append((ticker, active, linked))
    return sorted(result, key=lambda x: (not bool(x[2]), -len(x[1]), -sum(p['premium'] for p in x[1]), x[0]))

def order_row(ticker, p):
    return {'Contract': f"{ticker} {p['strike']:g}{p['type'][0].lower()} {datetime.fromisoformat(p['expiry']).strftime('%-m/%-d/%Y')}",
            'Printed (PT)': f"{p['date']} {p.get('time','')}",
            'Premium': str(p.get('premium_display') or f"${p['premium']:,.0f}"),
            'Filters': p.get('filters','')}

def render():
    st.title('🤫 Wells Fargo Whispers')
    st.write('Smaller names with at least two distinct orders backing the same direction, and time left for the thesis to play out. A verified non-earnings event before expiration puts a name higher on the list, but it isn’t required.')
    s, meta = load('snapshot.json'), load('whispers.json')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    prints = s.get('prints',[])
    days = sorted({p['date'] for p in prints if p.get('date') and p['date'] <= today}, reverse=True)
    if not days:
        st.info('No saved RAMBO orders yet.')
        return
    selected = st.selectbox('Scan window', ['All saved history', *days])
    day = None if selected == 'All saved history' else selected
    info = meta.get('sessions',{}).get(day or days[0],{})
    caps = {}
    for observed_day, session in sorted(meta.get('sessions',{}).items()):
        if observed_day <= (day or today):
            caps.update(session.get('caps',{}))
    st.caption(f'Saved RAMBO sample: {days[-1]} through {days[0]}.')
    min_dte = st.slider('Minimum calendar days to expiry', min_value=2, max_value=30, value=MIN_DTE)
    st.caption('Two distinct ask-side orders must each clear the expiry buffer. Opposing ask-side flow anywhere in the selected window disqualifies the ticker. Duplicate filter hits count once. Verified market cap up to $20B.')
    rows = leads(prints, caps, s.get('events',[]), day, today, min_dte)
    if not rows:
        st.info('No fully verified Whispers in this window.')
    pending = leads(prints, caps, s.get('events',[]), day, today, min_dte, pending=True)
    if pending:
        st.subheader('Flow matches · market cap pending')
        st.caption('These names cleared the flow and expiry checks. They are not qualified Whispers until market cap is verified.')
        st.dataframe([{'Ticker': ticker, 'Side': orders[0]['type'].lower()[0].upper(),
                       'Orders': len(orders), 'Sessions': len({p['date'] for p in orders}),
                       'Latest order': max(p['date'] for p in orders),
                       'Approx. premium': sum(p['premium'] for p in orders),
                       'RAMBO': ', '.join(e['title'] for e in events)}
                      for ticker, orders, events in pending], hide_index=True, width='stretch')
        ticker = st.selectbox('Inspect corroborating orders', [r[0] for r in pending])
        orders = next(r[1] for r in pending if r[0] == ticker)
        st.dataframe([order_row(ticker,p) for p in orders], hide_index=True, width='stretch')
    for ticker, orders, events in rows:
        calls = orders[0]['type'].lower().startswith('c')
        with st.container(border=True):
            st.subheader(('📞 ' if calls else '🩸 ') + ticker)
            st.caption(f"${caps[ticker]/1e9:g}B displayed market cap · {len(orders)} distinct {'call' if calls else 'put'} orders")
            for e in events:
                st.write(f"🪃 {e['date']} · {e['title']}")
                if e.get('url'):
                    st.link_button('Company source ↗',e['url'])
            if not events:
                st.caption('No confirmed RAMBO match in saved coverage.')
            if ticker in info.get('earnings_day',[]):
                st.warning('The source flagged earnings at 0 DTE. Treat this as earnings-sensitive flow.')
            st.dataframe([order_row(ticker,p) for p in orders], hide_index=True, width='stretch')
    st.caption('Premium is rounded. A single order never qualifies. Ask-side prints may be hedges or part of activity outside this sample.')
