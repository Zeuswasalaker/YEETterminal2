"""Meme Swan dashboard, with separately sourced Founder and RAMBO context."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
from html import escape
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

def cumulative(raw, days):
    window = raw[raw.date.isin(days)]
    base = score(window[window.ticker.isin(BENCHMARK)])
    board = []
    for ticker, group in window[~window.ticker.isin(BENCHMARK)].groupby('ticker'):
        read = score(group)
        row = {'Ticker': ticker, 'Score': read['score'],
               'Vs broad (pts)': read['score'] - base['score'] if base else None,
               'Sessions': group.date.nunique(), 'Alerts': read['prints'],
               'Premium (approx.)': read['premium'], 'Call premium %': read['call_dollars']}
        for day in days:
            daily = score(group[group.date.eq(day)])
            row[day] = daily['score'] if daily else None
        board.append(row)
    return sorted(board, key=lambda r: (-r['Score'], -r['Sessions'], -r['Alerts'], -r['Premium (approx.)'], r['Ticker'])), base


def render():
    snap = load('meme_swan.json')
    founders = load('founders.json')
    rambo = load('snapshot.json')
    today = datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    st.title('🚀 MEME LAB')
    st.write('Which memes are running with the market, and which are doing their own thing? Meme Swan compares filtered options alerts with SPY, QQQ and IWM. The score combines call share of premium (70%) and call share of alerts (30%). Above 50 leans calls; below 50 leans puts. The leaderboard pools the captured alerts across sessions, and the session columns show whether the lean held up day to day. This is a flow read, not a price forecast.')
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
    st.subheader('👑 Meme Swan leaderboard')
    window_options = {'Last 2 captured sessions': 2, 'Last 3 captured sessions': 3, 'All captured sessions': len(days)}
    window_label = st.selectbox('Leaderboard window', list(window_options))
    window_days = days[:window_options[window_label]]
    leaderboard, pooled_base = cumulative(raw, window_days)
    if leaderboard:
        leader = leaderboard[0]
        ticker_label = escape(str(leader['Ticker']))
        st.markdown(
            f'<div style="background:linear-gradient(120deg,#fff0b0,#d6a849);color:#382609;'
            f'padding:18px 22px;border-radius:16px;border:1px solid #f8dc91;margin:8px 0 14px;">'
            f'<strong>👑 TOP MEME · {ticker_label}</strong><br>'
            f'<span style="font-size:25px;font-weight:800">{leader["Score"]:.1f}/100</span>'
            f' &nbsp;·&nbsp; {leader["Alerts"]} alerts across {leader["Sessions"]} of {len(window_days)} sessions'
            f' &nbsp;·&nbsp; ${leader["Premium (approx.)"]:,.0f} in displayed premium</div>',
            unsafe_allow_html=True,
        )
        baseline = f" · broad flow {pooled_base['score']:.1f}/100" if pooled_base else ''
        st.caption(f'{window_days[-1]} to {window_days[0]}{baseline}. Each dated column shows that session’s score; blanks mean no qualifying alerts were captured.')
        table = pd.DataFrame(leaderboard)
        table.loc[0, 'Ticker'] = '👑 ' + table.loc[0, 'Ticker']
        formats = {c: st.column_config.NumberColumn(format='%.1f') for c in ['Score','Vs broad (pts)','Call premium %',*window_days]}
        formats['Premium (approx.)'] = st.column_config.NumberColumn(format='dollar')
        st.dataframe(table, hide_index=True, width='stretch', column_config=formats)
        st.caption('Ranked by pooled score. Ties favor more sessions, then more alerts and premium. Check the session and alert counts: one alert can top the board. Repeated alerts may overlap.')
    else:
        st.info('No qualifying meme alerts in this window.')
    st.subheader('🔎 Session consoles')
    st.caption('The consoles below use the individual session selected above. Saved Founder and RAMBO orders are separate from Meme Swan scores.')
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
