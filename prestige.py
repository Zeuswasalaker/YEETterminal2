"""Evidence-backed Prestige snapshot display. No credentials or private filter settings."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

STATUSES = ['Current Prestige','On Deck','Approaching','Watching','Expired']

def visible_cards(snapshot, today):
    cards=[]
    for original in snapshot.get('cards',[]):
        c=dict(original)
        if datetime.strptime(c['expiry'], '%m/%d/%Y').date()<today:
            c['status']='Expired'
        cards.append(c)
    return cards

def validate_snapshot(snapshot):
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get('cards'),list):
        raise ValueError('Snapshot needs a cards list.')
    if snapshot['cards']:
        for key in ['captured_at','source_time','coverage_start','spot','alert_count']:
            if key not in snapshot: raise ValueError(f'Missing {key}')
        if not isinstance(snapshot['spot'],(int,float)) or snapshot['spot']<=0: raise ValueError('Invalid SPY price.')
    for item in snapshot['cards']:
        for key in ['contract','type','expiry','status','strike','alerts','first','last','last_side','last_premium','last_price']:
            if key not in item: raise ValueError(f'Missing {key}')
        if item['status'] not in STATUSES or item['type'] not in ['call','put']: raise ValueError('Unknown contract type or status.')
        datetime.strptime(item['expiry'],'%m/%d/%Y')
    return snapshot


def admin_upload(admin,snapshot):
    import streamlit as st
    with st.expander('Milt’s controls / load saved contracts'):
        if admin():
            uploaded=st.file_uploader('Saved Prestige data (.json)',type=['json'],key='prestige_upload')
            if uploaded and st.button('Show these contracts',type='primary'):
                try:
                    incoming=validate_snapshot(json.load(uploaded))
                    st.session_state.prestige_snapshot=incoming
                    st.rerun()
                except Exception as exc: st.error(f'Could not read that snapshot: {exc}')
            st.download_button('Download saved contracts',json.dumps(snapshot,indent=2),file_name='prestige.json',mime='application/json')
            st.caption('Uploads preview contracts in your session. For a shared board without committing data to GitHub, set PRESTIGE_SNAPSHOT_JSON in Streamlit Secrets to the snapshot JSON string. Neither method starts automatic collection.')


def gold_tile(contract,spot):
    symbol='$SPY'
    strike=f"{float(contract['strike']):g}"
    side='CALL' if contract['type']=='call' else 'PUT'
    icon='📞' if side=='CALL' else '🩸'
    expiry=datetime.strptime(contract['expiry'],'%m/%d/%Y').strftime('%b %d, %Y')
    status=escape(contract['status'])
    try:
        first=datetime.strptime(contract['first'],'%Y/%m/%d %H:%M:%S').strftime('%b %d, %Y · %I:%M:%S %p')
    except (KeyError,ValueError,TypeError):
        first='Not recorded'
    return f'<article class="gold-contract" aria-label="SPY {strike} {side} expiring {expiry}"><div class="gold-top"><span>{icon} {side}</span><span>{symbol}</span></div><div class="gold-strike">{strike}<span>{"c" if side=="CALL" else "p"}</span></div><div class="gold-expiry">Expires {expiry}</div><div class="gold-status">{status}</div><div class="gold-first"><span>First spotted</span><strong>{escape(first)}</strong><small>Earliest alert in this saved window · UW clock</small></div><div class="gold-foot">{contract["alerts"]} saved alerts · ${abs(float(contract["strike"])-spot):.2f} from strike<br>At the saved SPY price</div></article>'


def render(admin):
    import streamlit as st
    path=Path(__file__).parent/'data'/'prestige.json'
    if 'prestige_snapshot' not in st.session_state:
        try:
            private=st.secrets.get('PRESTIGE_SNAPSHOT_JSON','')
        except Exception:
            private=''
        try:
            initial=json.loads(private) if private else json.loads(path.read_text())
            st.session_state.prestige_snapshot=validate_snapshot(initial)
        except Exception:
            st.error('Saved Prestige data could not be read. Check the snapshot format in Milt’s controls.')
            st.session_state.prestige_snapshot={'cards':[]}
    snapshot=st.session_state.prestige_snapshot
    today=datetime.now(ZoneInfo('America/New_York')).date()
    cards=visible_cards(snapshot,today)
    st.markdown('''<style>
.gold-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;margin:22px 0 30px}
.gold-contract{aspect-ratio:1;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center;min-width:0;padding:24px;border-radius:12px;border:2px solid #f1d17b;background:linear-gradient(128deg,#fff0b1 0%,#dcae43 22%,#f5d580 43%,#b77d22 72%,#e8c66b 100%);box-shadow:inset 2px 2px 1px #fff7ce,inset -3px -4px 2px #805313,0 7px 0 #674411,0 13px 20px #0005;color:#30220a;font-family:"Trebuchet MS",Arial,sans-serif}
.gold-top{display:flex;justify-content:space-between;gap:8px;font-size:12px;font-weight:900;letter-spacing:.07em;text-shadow:0 1px 0 #fff3b5}
.gold-strike{font:900 clamp(34px,4vw,58px)/1.1 "Arial Rounded MT Bold","Trebuchet MS",Arial,sans-serif;letter-spacing:-.055em;color:#392607;margin:16px 0 6px;text-shadow:0 1px 0 #fff4c0,0 -1px 1px #77511e}
.gold-strike span{font-size:.65em;margin-left:3px}
.gold-expiry{font-weight:800;font-size:14px;color:#352407;text-shadow:0 1px 0 #fff1b0}
.gold-status{align-self:flex-start;margin:14px 0 10px;padding:5px 9px;border:1px solid #64420c77;border-radius:6px;background:#fff1bd77;font-size:11px;font-weight:800;color:#342409}
.gold-first{display:flex;flex-direction:column;gap:3px;margin:0 0 7px;padding:7px 0;border-top:1px solid #62420d44}
.gold-first>span{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#46300e}
.gold-first strong{font-size:12px;line-height:1.4;color:#30220a}
.gold-first small{font-size:9px;line-height:1.4;color:#46300e}
.gold-foot{font-size:11px;line-height:1.6;color:#3c2a0b;margin-top:auto;padding-top:8px}
@media(max-width:900px){.gold-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.gold-strike{font-size:46px}}
@media(max-width:480px){.gold-grid{grid-template-columns:1fr;gap:22px;max-width:340px;margin-left:auto;margin-right:auto}.gold-strike{font-size:58px}}
@media(forced-colors:active){.gold-contract{background:Canvas;color:CanvasText;border:2px solid CanvasText;box-shadow:none}.gold-contract *{color:CanvasText;text-shadow:none}}
</style>''',unsafe_allow_html=True)
    st.title('The Prestige')
    st.markdown('<div class="eyebrow">THE FLOW / THE MOVE AWAY / THE RETURN</div>',unsafe_allow_html=True)
    st.write('The gold-brick watchlist. Watch it move away. Watch it come back.')
    st.warning('Saved research snapshot. Continuous collection and live SPY prices are not connected. Status describes the last observed data, not the market right now.')
    if not snapshot.get('cards'):
        st.info('The Prestige board is ready. No shared alert snapshot has been published yet.')
        tabs=st.tabs(['Current Prestige','On Deck','Approaching','Watching / Expired'])
        for tab,text in zip(tabs,['Observed move away and return; still near the strike at the snapshot.','Near the strike, awaiting a complete Prestige sequence.','Outside the zone and moving closer; watch for re-entry.','Track remaining candidates and expired contracts.']):
            with tab: st.write(text)
        admin_upload(admin,snapshot)
        return
    st.caption(f"Captured: {snapshot['captured_at']} • Latest source alert: {snapshot['source_time']} • Source clock timezone unverified; times shown exactly as UW.")
    counts={status:sum(c['status']==status for c in cards) for status in STATUSES}
    a,b,c,d=st.columns(4)
    a.metric('Return observed',counts['Current Prestige'])
    b.metric('On deck',counts['On Deck'])
    c.metric('Approaching',counts['Approaching'])
    d.metric('Last observed SPY',f"${snapshot['spot']:.2f}")
    st.caption('First spotted means the earliest alert in the captured window, not necessarily the contract’s first-ever appearance. Source clock timezone has not been verified.')
    st.caption(f"{snapshot['alert_count']} displayed UW alert rows grouped into {len(cards)} contracts. Coverage: {snapshot['coverage_start']} through {snapshot['source_time']}. Alert counts are captured rows, not verified unique executions. Premiums are rounded source labels, not summed totals.")
    side=st.radio('Show',['All','Calls','Puts'],horizontal=True)
    tabs=st.tabs(['Current Prestige','On Deck','Approaching','Watching / Expired'])
    descriptions=[
        'A near → away → return sequence appears in the captured SPY observations, and price was still in the Magic Zone at the snapshot. Review the evidence before treating it as a play.',
        'Inside the Magic Zone at the snapshot, but the captured history does not establish a full move-away-and-return sequence. Trigger: observe the move away, then the return before expiration.',
        'Outside the zone, within the monitoring buffer, with distance shrinking across the last six captured SPY observations. Trigger: re-enter the zone; a full Prestige also needs the earlier sequence.',
        'Outside the zone without a qualifying approach, or past expiration. Trigger: renewed approach and a verified return while the contract is active.'
    ]
    for i,tab in enumerate(tabs):
        with tab:
            st.write(descriptions[i])
            wanted=[STATUSES[i]] if i<3 else ['Watching','Expired']
            selected=[x for x in cards if x['status'] in wanted and (side=='All' or x['type']==('call' if side=='Calls' else 'put'))]
            selected.sort(key=lambda x:(datetime.strptime(x['expiry'],'%m/%d/%Y'),abs(x['strike']-snapshot['spot'])))
            if not selected: st.info('No contracts in this group for the saved snapshot.')
            if selected:
                st.markdown('<div class="gold-grid">'+''.join(gold_tile(item,snapshot['spot']) for item in selected)+'</div>',unsafe_allow_html=True)
                with st.expander('Open the details / last alert & return evidence'):
                    chosen=st.selectbox('Pick a contract',[item['contract'] for item in selected],key=f'prestige_details_{i}')
                    contract=next(item for item in selected if item['contract']==chosen)
                    st.write(f"Last saved alert: {contract['last']} · {contract['last_side']} · {contract['last_premium']} premium")
                    st.write(f"Option price at that alert: {contract['last_price']}. This is historical, not a current quote.")
                    if contract.get('away') and contract.get('returned'):
                        st.write(f"First saved contract alert: {contract['first']}")
                        st.write(f"SPY outside the zone: {contract['away']}")
                        st.write(f"SPY back inside: {contract['returned']}")
                        st.caption('These are irregular SPY observations from saved alerts, not a continuous price history. Short boundary crossings can qualify. A return is not proof of a winning trade.')
                    else:
                        st.caption('The saved data does not establish the full move-away-and-return sequence for this contract.')
    with st.expander('Reading the board'):
        st.write('Calls and puts remain separate. An ask-side print is not proof of an opening directional trade. This board tracks observed price behavior and expiration; it does not estimate ITM odds or recommend an entry.')
        st.write('The initial capture covers only the displayed 250-row window. Older moves may be missing. Expired contracts are removed from active groups as the date advances. Private filter thresholds stay out of the site source and member explanations.')
    admin_upload(admin,snapshot)
