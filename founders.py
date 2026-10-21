"""Founder ticker coverage: independent company events and captured flow."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from urllib.parse import quote

ROOT=Path(__file__).parent

def matching_events(flow,events,as_of):
    """An event must occur after the print and before expiry; exclude earnings."""
    printed=str(flow.get('date',''))[:10]
    expiry=str(flow.get('expiry',''))[:10]
    if not printed or not expiry: return []
    return [e for e in events if e.get('ticker')==flow.get('ticker') and e.get('status')=='Confirmed' and not e.get('earnings_related',False) and max(printed,as_of)<=e['date']<=expiry]

def render(admin):
    import streamlit as st
    snapshot=json.loads((ROOT/'data'/'founders.json').read_text())
    registry=json.loads((ROOT/'data'/'founder_filters.json').read_text())
    today=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
    st.markdown('''<style>
.founder-title{background:none!important;-webkit-text-fill-color:#e7cb85!important;color:#e7cb85!important;font-family:"Trebuchet MS",Arial,sans-serif!important;text-shadow:1px 2px 0 #796035,3px 4px 0 #0a2028;font-size:clamp(30px,5vw,46px)!important}
.founder-intro{font:600 16px/1.7 "Trebuchet MS",Arial,sans-serif;color:#c3d8ca;margin-bottom:22px}
.founder-card{border:1px solid #dabd7255;border-radius:18px;padding:22px;background:linear-gradient(130deg,#294039,#173038);box-shadow:0 5px 0 #0b2027;margin:14px 0 20px}
.founder-card h3{font:800 23px/1.3 "Trebuchet MS",Arial,sans-serif!important;color:#ead296!important;margin:0 0 10px}
.founder-card p{color:#bcd3c9;font:500 14px/1.7 "Trebuchet MS",Arial,sans-serif;margin:8px 0}
.founder-ticker{font:900 27px "Trebuchet MS",Arial,sans-serif;color:#b8ec73}
.founder-note{font-size:12px;color:#9fbbb0}
.founder-preview{background:linear-gradient(130deg,#4a4636,#2a3735);border:1px dashed #ddc17c88;border-radius:16px;padding:18px 22px;margin:8px 0 16px;color:#e8d59f;font:800 15px/1.6 "Trebuchet MS",Arial,sans-serif}
.st-key-founder_request_ticker input:disabled{background:#293735!important;color:#a7b0a5!important;-webkit-text-fill-color:#a7b0a5!important;opacity:1!important}
.st-key-milt_founder [data-testid="stExpander"] summary p{color:#ff8b82!important}
</style>''',unsafe_allow_html=True)
    st.markdown('<h1 class="founder-title">👑 OG/ Founder level perks</h1><div class="founder-intro">A little extra love for the people giving a little extra. 💛<br>As a thank-you for their generosity, <strong>Founding-level members can request ANY ticker they choose</strong> for our <strong>flow and RAMBO search lists</strong>, then check back here whenever they please. Enter a ticker below to request coverage.</div>',unsafe_allow_html=True)
    st.markdown('<div class="founder-preview">👑 REQUEST YOUR FOUNDER TICKER HERE</div>',unsafe_allow_html=True)
    requested=st.text_input('Founding member ticker requests',placeholder='Enter a ticker, e.g. PLTR',key='founder_request_ticker',max_chars=12).strip().upper().lstrip('$')
    if requested:
        if requested.replace('.','').replace('-','').isalnum() and requested[0].isalpha():
            request_url='mailto:milt@theyeet.com?subject='+quote('Founder ticker request: '+requested,safe='')+'&body='+quote('Hi Milt,\n\nPlease add '+requested+' to my Founder ticker coverage.\n\nThank you!',safe='')
            st.link_button('✉️ Email '+requested+' request to Milt',request_url)
            st.caption('Opens your email app with the ticker filled in. Send it to Milt, and he’ll add it to the coverage list.')
        else:
            st.warning('Use a valid ticker symbol with letters, numbers, dots or hyphens.')
    ticker=st.pills('Your requested tickers',registry['tickers'],default=registry['tickers'][0],selection_mode='single') or registry['tickers'][0]
    company=snapshot['companies'].get(ticker,{'name':ticker,'ir_url':'','event_note':'Your ticker is on the research list. Company events are still being checked.'})
    st.markdown(f'<div class="founder-ticker">${escape(ticker)} <span style="font-size:16px;color:#c0d5c7">{escape(company["name"])}</span></div>',unsafe_allow_html=True)
    st.caption(('Research pending for '+ticker if company.get('event_note','').startswith('Added to Founder coverage.') else 'Company research checked '+snapshot['research_as_of'])+' · Saved results, not a streaming feed.')
    events=[e for e in snapshot['events'] if e['ticker']==ticker and e['end_date']>=today]
    all_flows=[f for f in snapshot.get('flows',[]) if f['ticker']==ticker]
    flows=[f for f in all_flows if f['expiry']>=today]
    a,b=st.columns(2)
    with a:
        st.subheader('📅 What’s coming up?')
        if not events:
            st.markdown(f'<div class="founder-card"><h3>Nothing confirmed here yet.</h3><p>{escape(company["event_note"])}</p></div>',unsafe_allow_html=True)
        for e in events:
            pretty=datetime.fromisoformat(e['date']).strftime('%b %d')
            if e['end_date']!=e['date']:pretty+='–'+datetime.fromisoformat(e['end_date']).strftime('%d')
            st.markdown(f'<div class="founder-card"><h3>{escape(e["title"])}</h3><div class="pill">📅 {pretty}</div><div class="pill">{escape(e["category"])}</div><p>{escape(e["summary"])}</p></div>',unsafe_allow_html=True)
            st.link_button('Company’s event details ↗',e['url'])
        if company.get('ir_url'):st.link_button('Company investor page ↗',company['ir_url'])
    with b:
        st.subheader('🐋 What’s showing up?')
        if snapshot.get('flow_as_of') and all_flows:
            st.caption('Flow checked '+snapshot['flow_as_of']+' · '+str(len(flows))+' captured prints with open expirations')
        checks=[c for c in snapshot.get('flow_checks',[]) if c['ticker']==ticker]
        success=[c for c in checks if c.get('status')=='checked']
        if not flows:
            if len(success)==len(registry['filters']):
                st.markdown('<div class="founder-card"><h3>No matches in the checked window.</h3><p>All six filters were checked. That’s a result, not a reason to force a play.</p></div>',unsafe_allow_html=True)
            else:
                st.markdown('<div class="founder-card"><h3>No verified flow update yet.</h3><p>The latest company-event research is on the left. Options activity has its own check, so a quiet-looking box here doesn’t mean there were no trades.</p></div>',unsafe_allow_html=True)
        for flow in sorted(flows,key=lambda x:(x.get('date',''),x.get('time','')),reverse=True):
            icon='📞' if flow['type']=='call' else '🩸'
            linked=matching_events(flow,snapshot['events'],today)
            status='🧩 Event before expiration' if linked else '👀 Flow watch · no confirmed event match'
            st.markdown(f'<div class="founder-card"><h3>{icon} ${ticker} {escape(str(flow["strike"]))}{"c" if flow["type"]=="call" else "p"}</h3><div class="pill">{status}</div><p>Expires {escape(flow["expiry"])} · {escape(str(flow.get("premium","")))} premium<br>Seen {escape(flow["date"])} {escape(flow.get("time",""))}<br>Filters: {escape(", ".join(flow.get("filters",[])))}</p></div>',unsafe_allow_html=True)
            st.caption(str(flow.get('size',''))+' contracts · '+flow.get('side','')+' side · Time shown in Pacific. Premium rounded as displayed by UW.')
            if linked:st.write('Dates line up with: '+', '.join(e['title'] for e in linked)+'. Date overlap alone does not establish why the trade was placed.')
        st.caption('Filters: '+', '.join(f['name'] for f in registry['filters']))
        if snapshot.get('flow_scope') and all_flows:st.caption(snapshot['flow_scope'])
    if all_flows:
        with st.expander('📚 All captured prints, including expired contracts'):
            import pandas as pd
            st.dataframe(pd.DataFrame([{'Printed (Pacific)':f['date']+' '+f['time'],'Contract':'$'+f['ticker']+' '+str(f['strike'])+('c' if f['type']=='call' else 'p'),'Expires':f['expiry'],'Premium (UW rounded)':f['premium'],'Side':f['side'],'Contracts':f['size'],'Filters':', '.join(f['filters'])} for f in all_flows]),hide_index=True,width='stretch')
    with st.expander('👀 How this perk works'):
        st.write('Founders can request companies for ongoing coverage. We check company announcements even when no option activity is showing up, and check option activity even when no event is announced. Earnings are not counted as RAMBO events.')
        st.write('Ask-side activity describes where a trade printed. It does not establish a buyer’s intent or distinguish a directional bet from a hedge. A repeat across filters is one captured print, not additional whale money.')
        st.write('When a verified event falls after a print and before its expiration, it becomes a research match. An industry booth or technical talk carries different weight from an investor day. A match is not an entry signal.')
    checks_path=ROOT/'data'/'founder_source_checks.json'
    if checks_path.exists():
        with st.expander('📌 Source check dates'):
            import pandas as pd
            source_checks=json.loads(checks_path.read_text())
            st.dataframe(pd.DataFrame([{k:v for k,v in row.items() if k not in ['text_excerpt','hash']} for row in source_checks.values()]),hide_index=True,width='stretch')
    with st.container(key='milt_founder'),st.expander('milt stuff'):
        if admin():
            st.caption('Founder membership verification is not connected; the page follows existing site access settings.')
            st.write('Dedicated checks replace only the ticker restriction. Original saved filters stay unchanged. NAUTILUS otherwise excludes NVDA.')
            for f in registry['filters']:
                st.link_button(f['name']+' · $'+ticker,f['ticker_urls'][ticker])
            st.download_button('Download Founder research',json.dumps(snapshot,indent=2),file_name='founders.json',mime='application/json')
