"""Meme Swan dashboard, with separately sourced Founder and RAMBO context."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import pandas as pd
import streamlit as st
from wari import score, gauge

DATA = Path(__file__).parent / 'data'
BENCHMARK = {'SPY', 'QQQ', 'IWM'}

def load(name):
    try:
        return json.loads((DATA / name).read_text())
    except (OSError, ValueError):
        return {}

def contract(r):
    strike = float(r['strike'])
    expiry = datetime.fromisoformat(r['expiry'])
    suffix = 'c' if str(r['type']).lower() in ('call', 'c') else 'p'
    return f"{r['ticker']} {strike:g}{suffix} {expiry.month}/{expiry.day}/{expiry.year}"

def render():
    snap = load('meme_swan.json')
    founders = load('founders.json')
    rambo = load('snapshot.json')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    st.title('🚀 MEME LAB')
    st.write('Meme Swan tracks which names are breaking from SPY, QQQ and IWM in the options tape.')
    if snap.get('source_url'):
        st.link_button('Open Meme Swan ↗', snap['source_url'])
    st.caption(snap.get('coverage', 'No Meme Swan snapshot loaded.'))
    raw = pd.DataFrame(snap.get('alerts', []), columns=['date','time','ticker','type','strike','expiry','premium','size','side','ask_pct','spot'])
    days = sorted(raw.date.unique(), reverse=True)
    day = st.selectbox('Meme Swan session', days) if days else None
    tape = raw[raw.date.eq(day)]
    market = tape[tape.ticker.isin(BENCHMARK)]
    memes = tape[~tape.ticker.isin(BENCHMARK)]
    base, basket = score(market), score(memes)
    cols = st.columns(3)
    for col, label, value in zip(cols, ('Broad flow', 'Meme basket', 'Meme vs broad'), (
        f"{base['score']:.1f}/100" if base else '—',
        f"{basket['score']:.1f}/100" if basket else '—',
        f"{basket['score']-base['score']:+.1f} pts" if basket and base else '—')):
        col.metric(label, value)
    st.caption('70% call premium share + 30% call alert share. 50 is balanced. This compares filtered flow within a session; it does not measure price divergence, predict returns, or establish trade intent.')
    leaderboard = []
    for ticker, group in memes.groupby('ticker'):
        s = score(group)
        gap = s['score'] - base['score'] if base else None
        leaderboard.append({'Ticker':ticker, 'Score':round(s['score'],1), 'Vs broad (pts)':round(gap,1) if gap is not None else None,
                            'Alerts':s['prints'], 'Premium (approx.)':s['premium'], 'Call premium %':round(s['call_dollars'],1)})
    leaderboard.sort(key=lambda r: -r['Premium (approx.)'])
    st.subheader('🔥 Top hits')
    if leaderboard:
        st.dataframe(pd.DataFrame(leaderboard), hide_index=True, width='stretch',
                     column_config={'Premium (approx.)':st.column_config.NumberColumn(format='dollar')})
        st.caption('Ranked by displayed alert premium. Repeated alerts may overlap, and a single alert can swing a score. Missing tickers were not observed in this sample.')
    else:
        st.info('No qualifying meme alerts visible in the selected sample.')
    watch = ['GME'] + [r['Ticker'] for r in leaderboard if r['Ticker'] != 'GME'][:6]
    for ticker, pane in zip(watch, st.tabs(watch)):
        with pane:
            console(ticker, tape[tape.ticker.eq(ticker)], base, founders, rambo, today)

def console(ticker, alerts, base, founders, rambo, today):
    company = founders.get('companies', {}).get(ticker, {})
    st.subheader(f'{ticker} console' + (f" · {company['name']}" if company.get('name') else ''))
    s = score(alerts)
    if s:
        cols = st.columns(3)
        cols[0].metric('Meme Swan', f"{s['score']:.1f}/100")
        cols[1].metric('Vs broad flow', f"{s['score']-base['score']:+.1f} pts" if base else '—')
        cols[2].metric('Captured alerts', s['prints'])
        gauge(s['score'])
        st.dataframe(pd.DataFrame([{'Contract':contract(r),'Feed time':r['time'],'Premium':f"${r['premium']:,.0f}",'Side':r['side'],'Size':r['size']}
                                   for r in alerts.sort_values('premium',ascending=False).to_dict('records')]),
                     hide_index=True,width='stretch')
    else:
        st.info('Meme Swan score unavailable: no qualifying alerts visible for this ticker in the selected sample.')
    a,b = st.columns(2)
    events = [e for e in founders.get('events', []) + rambo.get('events', [])
              if e.get('ticker') == ticker and e.get('status') == 'Confirmed' and not e.get('earnings_related')]
    events = list({(e.get('date'), e.get('title')):e for e in events}.values())
    with a:
        st.markdown('**📅 RAMBO & company events**')
        upcoming = [e for e in events if e.get('end_date',e['date']) >= today]
        if not upcoming:
            st.caption('No upcoming non-earnings event in saved coverage.')
        for e in sorted(events,key=lambda e:e['date'],reverse=True)[:8]:
            past = e.get('end_date',e['date']) < today
            st.write(f"**{e['date']} · {e['title']}**" + (' (past)' if past else ''))
            st.caption(e.get('category','Company event'))
            if e.get('url'):
                st.link_button('Event source ↗', e['url'])
        if company.get('ir_url'):
            st.link_button('Investor relations ↗', company['ir_url'])
    with b:
        st.markdown('**🐋 Saved Founder / RAMBO orders**')
        orders = {}
        for r in founders.get('flows', []) + rambo.get('prints', []):
            if r.get('ticker',r.get('underlying_symbol')) != ticker:
                continue
            r = dict(r,ticker=ticker)
            kind = str(r['type']).lower()[0]
            key = (r['date'],r.get('time'),kind,float(r['strike']),r['expiry'],str(r.get('size')))
            orders.setdefault(key,r)
        if not orders:
            st.caption('No saved orders for this ticker in these sources.')
        else:
            def table(rows):
                return pd.DataFrame([{'Contract':contract(r),'Printed':r['date'],'Premium':r.get('premium_display') or str(r.get('premium','')),
                                      'Side':r.get('side'),'Filters':', '.join(r['filters']) if isinstance(r.get('filters'),list) else r.get('filters',''),
                                      'Upcoming event overlap':', '.join(e['title'] for e in upcoming if r['date'] <= e['date'] <= r['expiry'] and 'corporate action' not in e.get('category','').lower()) or '—'}
                                     for r in sorted(rows,key=lambda r:(r['date'],r.get('time','')),reverse=True)])
            open_orders = [r for r in orders.values() if r['expiry'] >= today]
            if open_orders:
                st.dataframe(table(open_orders),hide_index=True,width='stretch')
            else:
                st.caption('No saved orders with unexpired contracts.')
            with st.expander('All saved orders, including expired'):
                st.dataframe(table(orders.values()),hide_index=True,width='stretch')
            st.caption('Unexpired contract dates do not establish an open position. Event overlap does not establish intent.')
