import hashlib
import hmac
import html
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from rambo import normalize, match

ROOT = Path(__file__).parent
LOGO = next((p for p in [ROOT/'assets'/'yeet-logo.png', ROOT/'assets'/'yeet-logo.jpeg', ROOT/'assets'/'yeet-logo.jpg'] if p.exists()), None)
st.set_page_config(page_title='The YEET | Terminal', page_icon=str(LOGO) if LOGO else 'Y',layout='wide')

def secret(key):
    try: return st.secrets.get(key,'')
    except Exception: return ''

access = secret('ACCESS_PASSWORD')
if access and not st.session_state.get('reader_access'):
    if LOGO: st.image(str(LOGO),width=180)
    st.title('The YEET / Terminal')
    password = st.text_input('Member access password',type='password')
    if st.button('Enter Terminal'):
        if hmac.compare_digest(password,access):
            st.session_state.reader_access=True
            st.rerun()
        else: st.error('Password not recognized.')
    st.stop()

st.markdown('''<style>
.stApp{background:radial-gradient(ellipse at 85% 0%,#30263b55,transparent 48%),linear-gradient(145deg,#101419,#151923);color:#eee9dd}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#20232d,#11151c);border-right:1px solid #ffffff12}
h1,h2,h3{color:#eee9dd}h1{font-family:Georgia,serif;font-size:4rem!important;letter-spacing:-.035em}
.eyebrow{letter-spacing:.22em;color:#cbb0f0;font-size:12px;margin-bottom:12px}.subhead{color:#b8bcc7;margin-bottom:26px;font-size:17px}
.card{padding:26px;border:1px solid #ffffff16;border-top:2px solid #cbb0f077;border-radius:18px;background:linear-gradient(130deg,#242936,#191f28);margin:8px 0 18px;box-shadow:0 12px 28px #00000030,inset 0 1px 0 #ffffff09}
.ticker{font:700 32px Georgia,serif;color:#d5bdf5}.pill{display:inline-block;border-radius:20px;background:#293f36;color:#c1f4d6;padding:5px 12px;font-size:12px;margin:8px 5px 8px 0;border:1px solid #b8efcf18}
.muted{color:#b5bcc8;font-size:14px;line-height:1.65}.money{font-size:30px;color:#f4e4a7;font-weight:700}
.stButton button,.stDownloadButton button,[data-testid="stLinkButton"] a{border-radius:11px!important;background:linear-gradient(180deg,#d5bdf5,#af8ed5)!important;color:#17121e!important;border:1px solid #e8d8ff88!important;box-shadow:0 5px 0 #674881,0 8px 18px #00000033!important;transition:transform .15s,box-shadow .15s}
.stButton button:hover,.stDownloadButton button:hover,[data-testid="stLinkButton"] a:hover{transform:translateY(-2px);box-shadow:0 7px 0 #674881,0 12px 24px #00000044!important}
[data-testid="stMetric"]{background:linear-gradient(140deg,#242a36,#191e27);border:1px solid #ffffff16;padding:18px;border-radius:14px;box-shadow:0 8px 22px #00000022}
.soon-card{min-height:200px;padding:22px;border-radius:16px;background:linear-gradient(140deg,#302b3e,#202531);border:1px solid #cbb0f033;box-shadow:0 10px 25px #00000033;margin-bottom:15px}
.soon-label{color:#f4e4a7;font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px}.soon-title{font-size:17px;font-weight:600;margin:8px 0;line-height:1.4}.month-heading{margin:32px 0 16px;border-bottom:1px solid #ffffff16;padding-bottom:13px;font:600 26px Georgia,serif}
[data-testid="stExpander"]{background:#191e2780;border-radius:12px;border-color:#ffffff16}
@media(max-width:640px){h1{font-size:3rem!important}.card{padding:20px}.soon-card{min-height:unset}}
@media(prefers-reduced-motion:reduce){.stButton button,.stDownloadButton button,[data-testid="stLinkButton"] a{transition:none!important;transform:none!important}}
</style>''',unsafe_allow_html=True)

seed = json.loads((ROOT/'data'/'snapshot.json').read_text())
if 'snapshot' not in st.session_state: st.session_state.snapshot=seed
data=st.session_state.snapshot
today=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()

with st.sidebar:
    if LOGO: st.image(str(LOGO),width=170)
    st.markdown('### THE YEET\nTERMINAL')
    page=st.radio('Workspace',['RAMBO','Upload & publish','Event research','My tickers','Prestige','PARI / WARI'],label_visibility='collapsed')
    st.divider()
    st.caption('FLOW × COMPANY CATALYSTS')
    st.caption('Founding Members: ongoing ticker coverage')
    st.caption('Research snapshot, not a live price feed')

def admin():
    configured=secret('ADMIN_PASSWORD')
    if not configured:
        st.info('Admin editing is disabled. Configure ADMIN_PASSWORD in Streamlit Secrets to enable uploads and research edits.')
        return False
    if st.session_state.get('admin_access'): return True
    password=st.text_input('Admin password',type='password',key='admin_password')
    if st.button('Unlock admin'):
        if hmac.compare_digest(password,configured):
            st.session_state.admin_access=True
            st.rerun()
        else: st.error('Password not recognized.')
    return False

def download_snapshot():
    st.download_button('Download publishable snapshot',json.dumps(data,indent=2),file_name='snapshot.json',mime='application/json')
    st.caption('Uploads update your current session. To update the shared site, replace data/snapshot.json in GitHub with this download. Persistent shared storage is a later integration.')

if page=='RAMBO':
    st.markdown('<div class="eyebrow">THE YEET / RESEARCH TERMINAL</div><h1>RAMBO</h1><div class="subhead">Relations and Meeting Buy Opportunities</div>',unsafe_allow_html=True)
    c1,c2=st.columns([3,1])
    query=c1.text_input('Find a ticker',placeholder='SMTC, NVTS, IBRX…').strip().upper()
    historical=c2.toggle('View Oct 14 snapshot',value=False)
    as_of=seed['research_as_of'] if historical else today
    results=match(data['events'],data['prints'],as_of)
    st.caption(f"Flow imported: {data.get('flow_imported_at','Unknown')} · Events verified: {data.get('events_checked_at','Unknown')} · Viewing event windows as of {as_of}")
    if today>data['research_as_of']: st.info('The supplied research is historical. Upload fresh exports and recheck event sources before using it as current research.')
    a,b,c=st.columns(3)
    a.metric('Matched events',len(results));b.metric('Flow tickers',len(set(p['underlying_symbol'] for p in data['prints'])));c.metric('Observed records',len(data['prints']))
    category=st.selectbox('Event scope',['All non-earnings events','Investor / analyst events only'])
    if query: results=[r for r in results if query in r['ticker']]
    if category.endswith('only'): results=[r for r in results if r['category']=='Investor / analyst']
    if not results: st.info('No confirmed events match these filters and expiration windows.')
    if results:
        st.subheader('Coming soon')
        st.caption('The three closest matching company catalysts')
        soon_columns=st.columns(min(3,len(results)))
        for column,event in zip(soon_columns,results[:3]):
            escape=lambda v: html.escape(str(v))
            days=event['days_until']
            timing='Happening now' if days<=0 else 'Tomorrow' if days==1 else f'In {days} days'
            pretty=datetime.fromisoformat(event['date']).strftime('%b %d, %Y')
            column.markdown(f'<div class="soon-card"><div class="soon-label">{escape(timing)}</div><div class="ticker">{escape(event["ticker"])}</div><div class="soon-title">{escape(event["title"])}</div><div class="muted">{pretty} · {escape(event["direction"])}</div></div>',unsafe_allow_html=True)
        st.subheader('Event calendar')
    current_month=None
    for event in results:
        month=event['date'][:7]
        if month!=current_month:
            label=datetime.fromisoformat(event['date']).strftime('%B %Y')
            st.markdown(f'<div class="month-heading">{label}</div>',unsafe_allow_html=True)
            current_month=month
        e=lambda v: html.escape(str(v))
        st.markdown(f'<div class="card"><span class="ticker">{e(event["ticker"])}</span><h3>{e(event["title"])}</h3><span class="pill">Confirmed event</span><span class="pill">{e(event["direction"])}</span><div>{e(event["date"])}{(" through "+e(event["end_date"])) if event["end_date"]!=event["date"] else ""} · {e(event.get("time","Time not announced"))}</div><p class="muted">{e(event["summary"])}</p></div>',unsafe_allow_html=True)
        with st.expander(f'{event["ticker"]}: contracts, sources and research note'):
            st.write(event['note'])
            st.link_button('Official company source',event['url'])
            frame=pd.DataFrame(event['prints'])
            columns=['date','time','strike','type','expiry','side','premium','size','filters','open_interest','volume']
            st.dataframe(frame[[k for k in columns if k in frame]],hide_index=True,width='stretch')
            st.caption('Exact duplicate records removed. Aggregated records may overlap constituent trades. ASK prints do not establish opening buys or prove a hedge. Snapshot OI and volume are not additive.')
            dates=sorted(set(str(p.get('next_earnings_date')) for p in event['prints'] if p.get('next_earnings_date')))
            if dates: st.caption('Earnings dates in uploaded exports, not independently refreshed: '+', '.join(dates))
elif page=='Upload & publish':
    st.title('Upload & publish')
    st.write('Drop your UW exports in together. The Terminal preserves filter provenance and matches contracts against confirmed event dates.')
    if admin():
        files=st.file_uploader('UW CSV exports',type='csv',accept_multiple_files=True)
        mode=st.radio('Import mode',['Merge into existing history','Replace all flow'])
        if st.button('Import and recalculate',disabled=not files):
            prints,warnings=normalize([(f.name,f.getvalue()) for f in files])
            for warning in warnings: st.warning(warning)
            if prints:
                if mode.startswith('Merge'):
                    index={p['record_id']:p for p in data['prints']}
                    for p in prints:
                        if p['record_id'] in index:
                            p['filters']=', '.join(sorted(set((index[p['record_id']].get('filters','')+', '+p['filters']).split(', '))))
                        index[p['record_id']]=p
                    prints=list(index.values())
                data['prints']=prints
                data['flow_imported_at']=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(timespec='seconds')
                data['research_as_of']=today
                st.success(f'Imported successfully. {len(prints)} observed records in this session.')
        st.divider()
        download_snapshot()
elif page=='Event research':
    st.title('Event research')
    st.write('Confirmed non-earnings events drive matches. New discoveries stay in review until the date and event type are verified.')
    st.dataframe(pd.DataFrame(data['events'])[['ticker','title','date','end_date','status','category']],hide_index=True,width='stretch')
    checks=ROOT/'data'/'source_checks.json'
    if checks.exists():
        monitored=json.loads(checks.read_text())
        st.subheader('Scheduled source checks')
        st.dataframe(pd.DataFrame([dict(url=url,**{k:v for k,v in row.items() if k!='text_excerpt'}) for url,row in monitored.items()]),hide_index=True,width='stretch')
        st.caption('A fetched or unchanged page does not reconfirm an event. Page changes require review.')
    else: st.caption('Source monitoring has not run yet. Run Check company event sources in GitHub Actions after upload.')
    if admin():
        with st.form('event'):
            ticker=st.text_input('Ticker').strip().upper()
            title=st.text_input('Event name')
            start=st.date_input('Start date')
            end=st.date_input('End date')
            url=st.text_input('Official source URL')
            category=st.selectbox('Category',['Investor / analyst','Company / technology','Shareholder meeting'])
            summary=st.text_area('What happens at the event')
            verified=st.checkbox('I verified the date and confirmed this is separate from earnings')
            submitted=st.form_submit_button('Add event')
        if submitted:
            if not ticker or not title or not url.startswith('https://') or end<start: st.error('Enter a ticker, title, HTTPS source and valid date range.')
            else:
                data['events'].append(dict(ticker=ticker,title=title,date=start.isoformat(),end_date=end.isoformat(),url=url,category=category,summary=summary,note='Added by Milt.',status='Confirmed' if verified else 'Needs review',earnings_related=False))
                data['events_checked_at']=datetime.now(ZoneInfo('America/Los_Angeles')).isoformat(timespec='seconds')
                st.success('Event added to this session.')
        download_snapshot()
elif page=='My tickers':
    st.title('Founding Member ticker coverage')
    st.write('Requested tickers are tracked independently of the broad filters. Membership verification and request delivery will be connected before member launch.')
    if admin():
        requested=st.text_input('Add a ticker to the coverage list').strip().upper()
        if st.button('Add to coverage') and requested:
            data['watchlist']=sorted(set(data.get('watchlist',[])+[requested]))
            st.success('Added to this session. Download the snapshot to publish it.')
        st.write(', '.join(data.get('watchlist',[])) or 'No requested tickers yet.')
        download_snapshot()
elif page=='Prestige':
    st.title('Prestige')
    st.info('Prestige research will appear here once the approved contract feed is connected. No signals or model thresholds are generated by this starter.')
else:
    st.title('PARI / WARI')
    st.info('The indicator feed is not connected yet. This page will display your actual calculated readings once supplied.')
