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
.stApp{background:radial-gradient(ellipse at 85% 0%,#07c99a08,transparent 48%),linear-gradient(145deg,#0f212f,#0d242b);color:#eee9dd}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#102632,#0c1e28);border-right:1px solid #ffffff12}
h1,h2,h3{color:#6ee947}h1{font-family:Arial,sans-serif;font-weight:900!important;font-size:4rem!important;letter-spacing:-.055em;background:linear-gradient(125deg,#b5ee32 5%,#08d88f 48%,#00afb5 90%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}h2{color:#73ed49!important}h3{color:#1cdfa0!important}
.eyebrow{letter-spacing:.22em;color:#13dca0;font-size:12px;margin-bottom:12px}.subhead{color:#b8bcc7;margin-bottom:26px;font-size:17px}
.card{padding:26px;border:1px solid #ffffff16;border-top:2px solid #13dca077;border-radius:18px;background:linear-gradient(130deg,#142f39,#102630);margin:8px 0 18px;box-shadow:0 12px 28px #00000030,inset 0 1px 0 #ffffff09}
.ticker{font:900 32px Arial,sans-serif;color:#89ed35}.pill{display:inline-block;border-radius:20px;background:#293f36;color:#c1f4d6;padding:5px 12px;font-size:12px;margin:8px 5px 8px 0;border:1px solid #b8efcf18}
.muted{color:#b5bcc8;font-size:14px;line-height:1.65}.money{font-size:30px;color:#f4e4a7;font-weight:700}
.stButton button,.stDownloadButton button,[data-testid="stLinkButton"] a{border-radius:11px!important;background:linear-gradient(135deg,#9bec3b,#06d595 55%,#00acb3)!important;color:#082b2a!important;border:1px solid #a2ee4a66!important;box-shadow:0 5px 0 #00685f,0 8px 18px #00000033!important;transition:transform .15s,box-shadow .15s}
.stButton button:hover,.stDownloadButton button:hover,[data-testid="stLinkButton"] a:hover{transform:translateY(-2px);box-shadow:0 7px 0 #00685f,0 12px 24px #00000044!important}
[data-testid="stMetric"]{background:linear-gradient(140deg,#152d38,#102630);border:1px solid #ffffff16;padding:18px;border-radius:14px;box-shadow:0 8px 22px #00000022}
.soon-card{min-height:200px;padding:22px;border-radius:16px;background:linear-gradient(140deg,#173334,#102630);border:1px solid #13dca033;box-shadow:0 10px 25px #00000033;margin-bottom:15px}
.soon-label{color:#f4e4a7;font-size:11px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:10px}.soon-title{font-size:17px;font-weight:600;margin:8px 0;line-height:1.4}.month-heading{margin:32px 0 16px;border-bottom:1px solid #ffffff16;padding-bottom:13px;color:#76eb48;font:700 26px Arial,sans-serif}
[data-testid="stExpander"]{background:#112b3780;border-radius:12px;border-color:#ffffff16}
/* Editorial typography: system sans, distinct weights, restrained emphasis. */
html,body,[data-testid="stAppViewContainer"],input,button,textarea,select{font-family:Inter,"Helvetica Neue",Arial,sans-serif!important;-webkit-font-smoothing:antialiased}
[data-testid="stMarkdownContainer"] p,[data-testid="stCaptionContainer"]{font-family:Inter,"Helvetica Neue",Arial,sans-serif;line-height:1.65}
.subhead{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:17px;line-height:1.5;letter-spacing:-.015em;color:#93abb4;margin:8px 0 30px}
.subhead strong{font-weight:650;color:#d7e6e7}
.eyebrow{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:10px;font-weight:700;letter-spacing:.2em;color:#32d5ac}
.ticker{font:800 30px/1.1 Inter,"Helvetica Neue",Arial,sans-serif;letter-spacing:-.035em;color:#a0ed45}
.card h3{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:23px!important;line-height:1.3!important;font-weight:700!important;letter-spacing:-.025em;color:#dce9e9!important;margin:12px 0 15px}
.pill{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-weight:600;font-size:11px;letter-spacing:.025em;background:#163b35;color:#8ddac1;padding:5px 11px}
.event-date{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:13px;line-height:1.6;color:#8ca8b0;margin:10px 0 12px}
.event-date strong{font-weight:650;color:#c7d9dc}
.muted{font-family:Inter,"Helvetica Neue",Arial,sans-serif;color:#a5b9c1;font-size:14px;line-height:1.8;letter-spacing:.003em}
.muted strong{font-weight:650;color:#d8e5e8}
.soon-label{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:10px;font-weight:700;letter-spacing:.14em;color:#4bd7ad}
.soon-title{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:16px;font-weight:650;letter-spacing:-.015em;line-height:1.5;color:#dae8e9;margin:11px 0}
.month-heading{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:24px;font-weight:750;letter-spacing:-.035em;color:#b7ced1}
h2{font-family:Inter,"Helvetica Neue",Arial,sans-serif!important;font-size:27px!important;letter-spacing:-.035em!important;font-weight:750!important}
[data-testid="stMetricLabel"] p{font-size:12px!important;font-weight:600!important;letter-spacing:.02em;color:#95b1b9}
[data-testid="stMetricValue"]{font-family:Inter,"Helvetica Neue",Arial,sans-serif;font-size:36px;font-weight:750;letter-spacing:-.045em;color:#dcebe9}
[data-testid="stCaptionContainer"]{color:#819ca7;font-size:12px}
[data-testid="stTextInput"] label p,[data-testid="stSelectbox"] label p{font-weight:600;font-size:13px;color:#bcd0d5}
.rambo-title{display:inline-block;font-size:clamp(3.5rem,9vw,5.4rem)!important;font-weight:900!important;line-height:1.08!important;letter-spacing:-.06em!important;margin:4px 0 14px!important;padding:0 0 14px!important;filter:drop-shadow(0 4px 0 #061b22) drop-shadow(0 10px 14px #0005);border-bottom:3px solid #2bd4a8}
.rambo-ticker{display:inline-block;font-size:34px;line-height:1.2;font-weight:900;letter-spacing:-.035em;color:#b3f35a;padding:6px 12px 7px;border-left:3px solid #22dbad;border-radius:0 9px 9px 0;background:linear-gradient(110deg,#244538,#183631);text-shadow:0 2px 2px #061c20;box-shadow:0 5px 12px #0003;margin:3px 0 8px}
.rambo-key{display:flex;flex-wrap:wrap;gap:10px 18px;padding:14px 18px;margin:12px 0 22px;border:1px solid #ffffff20;border-radius:12px;background:#102a32;color:#d1e2e4;font-size:13px;line-height:1.6}
.rambo-key strong{font-weight:750;color:#eff6f2}
@media(forced-colors:active){.rambo-title{-webkit-text-fill-color:CanvasText!important;background:none;filter:none}.rambo-ticker{color:CanvasText;border:1px solid CanvasText;text-shadow:none}}
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
    page=st.radio('Workspace',['RAMBO','Upload & publish','Event research','My tickers','Prestige','PARI'],label_visibility='collapsed')
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

def emphasize_summary(value):
    text=str(value)
    lead, separator, rest=text.partition('. ')
    if separator:
        return '<strong>'+html.escape(lead+'.')+'</strong> '+html.escape(rest)
    return html.escape(text)

def flow_label(direction):
    labels={'Call-side':'📞 Call flow','Put-side':'🛡️ Put flow','Mixed':'🔀 Mixed flow','Unclear':'❔ Unclear flow'}
    return labels.get(direction,html.escape(str(direction)))

if page=='RAMBO':
    st.markdown('<div class="eyebrow">THE YEET / RESEARCH TERMINAL</div><h1 class="rambo-title">RAMBO</h1><div class="subhead"><strong>Relations and Meeting</strong> Buy Opportunities</div>',unsafe_allow_html=True)
    c1,c2=st.columns([3,1])
    query=c1.text_input('Find a ticker',placeholder='$SMTC, $NVTS, $IBRX…').strip().upper().lstrip('
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
    st.markdown('<div class="rambo-key" role="note" aria-label="RAMBO icon key"><span><strong>Key</strong></span><span>📅 Event date</span><span>✅ Confirmed event</span><span>📞 Call flow</span><span>🛡️ Put flow</span><span>🔀 Mixed flow</span><span>⏳ Timing</span></div>',unsafe_allow_html=True)
    st.caption('Call / put labels describe the captured contracts, not a confirmed market direction. Put flow does not by itself establish a hedge.')
    if results:
        st.subheader('Coming soon')
        st.caption('The three closest matching company catalysts')
        soon_columns=st.columns(min(3,len(results)))
        for column,event in zip(soon_columns,results[:3]):
            escape=lambda v: html.escape(str(v))
            days=event['days_until']
            timing='Happening now' if days<=0 else 'Tomorrow' if days==1 else f'In {days} days'
            pretty=datetime.fromisoformat(event['date']).strftime('%b %d, %Y')
            column.markdown(f'<div class="soon-card"><div class="soon-label">⏳ {escape(timing)}</div><div class="ticker rambo-ticker">${escape(event["ticker"])}</div><div class="soon-title">{escape(event["title"])}</div><div class="muted">📅 <strong>{pretty}</strong><br>{flow_label(event["direction"])}</div></div>',unsafe_allow_html=True)
        st.subheader('Event calendar')
    current_month=None
    for event in results:
        month=event['date'][:7]
        if month!=current_month:
            label=datetime.fromisoformat(event['date']).strftime('%B %Y')
            st.markdown(f'<div class="month-heading">{label}</div>',unsafe_allow_html=True)
            current_month=month
        e=lambda v: html.escape(str(v))
        st.markdown(f'<div class="card"><span class="ticker rambo-ticker">${e(event["ticker"])}</span><h3>{e(event["title"])}</h3><span class="pill">✅ Confirmed event</span><span class="pill">{flow_label(event["direction"])}</span><div class="event-date">📅 <strong>{e(event["date"])}{(" through "+e(event["end_date"])) if event["end_date"]!=event["date"] else ""} · {e(event.get("time","Time not announced"))}</strong></div><p class="muted">{emphasize_summary(event["summary"])}</p></div>',unsafe_allow_html=True)
        with st.expander(f'${event["ticker"]}: contracts, sources and research note'):
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
    from prestige import render
    render(admin)
else:
    from pari import render
    render()
)
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
        st.markdown(f'<div class="card"><span class="ticker">{e(event["ticker"])}</span><h3>{e(event["title"])}</h3><span class="pill">Confirmed event</span><span class="pill">{e(event["direction"])}</span><div class="event-date"><strong>{e(event["date"])}{(" through "+e(event["end_date"])) if event["end_date"]!=event["date"] else ""} · {e(event.get("time","Time not announced"))}</strong></div><p class="muted">{emphasize_summary(event["summary"])}</p></div>',unsafe_allow_html=True)
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
    from prestige import render
    render(admin)
else:
    from pari import render
    render()
