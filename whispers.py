"""Research leads from the supplied RAMBO screens."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json

import streamlit as st

DATA = Path(__file__).parent / 'data'
CAP_LIMIT = 20_000_000_000

def load(name):
    try:
        return json.loads((DATA / name).read_text())
    except (OSError, ValueError):
        return {}

def leads(prints, caps, events, day, today):
    grouped = {}
    for p in prints:
        if p.get('date') != day or p.get('side') != 'ASK':
            continue
        ticker = p.get('underlying_symbol')
        kind = str(p.get('type', '')).lower()[:1]
        if kind in ('c','p') and ticker in caps and 0 < caps[ticker] <= CAP_LIMIT:
            grouped.setdefault(ticker, []).append(p)
    result = []
    for ticker, orders in grouped.items():
        if len({p['type'].lower()[0] for p in orders}) != 1:
            continue
        active = [p for p in orders if p.get('expiry','') >= today]
        if not active:
            continue
        linked = [e for e in events if e.get('ticker') == ticker and e.get('status') == 'Confirmed'
                  and not e.get('earnings_related') and 'corporate action' not in e.get('category','').lower()
                  and any(max(today,p['date']) <= e.get('date','') <= p['expiry'] for p in active)]
        result.append((ticker, active, linked))
    return sorted(result, key=lambda x: (not bool(x[2]), -len(x[1]), -sum(p['premium'] for p in x[1]), x[0]))

def render():
    st.title('🤫 Wells Fargo Whispers')
    st.write('Smaller names. One side of the tape. Something worth digging into. A verified non-earnings event before expiration puts a name higher on the list, but it isn’t required.')
    s, meta = load('snapshot.json'), load('whispers.json')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    days = sorted(meta.get('sessions',{}), reverse=True)
    if not days:
        st.info('Waiting for a verified screen with market-cap coverage.')
        return
    day = st.selectbox('Captured session', days)
    info = meta['sessions'][day]
    st.caption(info['coverage'])
    st.caption('Screen: observed market cap up to $20B and no opposing ask-side print in the captured RAMBO sample. Unverified caps stay out. This is filtered coverage, not the whole options tape.')
    rows = leads(s.get('prints',[]), info['caps'], s.get('events',[]), day, today)
    if not rows:
        st.info('No verified candidates in this captured window.')
    for ticker, orders, events in rows:
        calls = orders[0]['type'].lower().startswith('c')
        with st.container(border=True):
            st.subheader(('📞 ' if calls else '🩸 ') + ticker)
            st.caption(f"${info['caps'][ticker]/1e9:g}B displayed market cap · {len(orders)} captured {'call' if calls else 'put'} alerts")
            for e in events:
                st.write(f"🪃 {e['date']} · {e['title']}")
                if e.get('url'):
                    st.link_button('Company source ↗',e['url'])
            if not events:
                st.caption('No confirmed RAMBO match in saved coverage.')
            if ticker in info.get('earnings_day',[]):
                st.warning('The source flagged earnings at 0 DTE. Treat this as earnings-sensitive flow.')
            st.dataframe([{'Contract':f"{ticker} {p['strike']:g}{p['type'][0].lower()} {datetime.fromisoformat(p['expiry']).strftime('%-m/%-d/%Y')}",
                           'Premium':p.get('premium_display',p['premium']), 'Time (PT)':p.get('time',''),
                           'Filters':p.get('filters','')} for p in orders], hide_index=True, width='stretch')
    st.caption('Premium is rounded. A single alert is a lead, not repeat confirmation. Ask-side prints may be hedges or part of activity outside this sample.')
