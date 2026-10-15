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

def render(admin):
    import streamlit as st
    path=Path(__file__).parent/'data'/'prestige.json'
    if 'prestige_snapshot' not in st.session_state:
        st.session_state.prestige_snapshot=json.loads(path.read_text())
    snapshot=st.session_state.prestige_snapshot
    today=datetime.now(ZoneInfo('America/New_York')).date()
    cards=visible_cards(snapshot,today)
    st.title('The Prestige')
    st.markdown('<div class="eyebrow">THE FLOW / THE MOVE AWAY / THE RETURN</div>',unsafe_allow_html=True)
    st.write('Track the contracts. Watch the distance. Wait for the return.')
    st.warning('Saved research snapshot. Continuous collection and live SPY prices are not connected. Status describes the last observed data, not the market right now.')
    if not snapshot.get('cards'):
        st.info('The Prestige board is ready. No shared alert snapshot has been published yet.')
        tabs=st.tabs(['Current Prestige','On Deck','Approaching','Watching / Expired'])
        for tab,text in zip(tabs,['Observed move away and return; still near the strike at the snapshot.','Near the strike, awaiting a complete Prestige sequence.','Outside the zone and moving closer; watch for re-entry.','Track remaining candidates and expired contracts.']):
            with tab: st.write(text)
        return
    st.caption(f"Captured: {snapshot['captured_at']} • Latest source alert: {snapshot['source_time']} • Source clock timezone unverified; times shown exactly as UW.")
    counts={status:sum(c['status']==status for c in cards) for status in STATUSES}
    a,b,c,d=st.columns(4)
    a.metric('Return observed',counts['Current Prestige'])
    b.metric('On deck',counts['On Deck'])
    c.metric('Approaching',counts['Approaching'])
    d.metric('Last observed SPY',f"${snapshot['spot']:.2f}")
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
            for n,contract in enumerate(selected):
                distance=abs(contract['strike']-snapshot['spot'])
                color='#8fed38' if contract['type']=='call' else '#f0b189'
                st.markdown(f'''<div class="card"><div class="eyebrow">{escape(contract['status'])} / {contract['type'].upper()} WATCH</div>
<div class="ticker" style="color:{color}">SPY {escape(contract['contract'])}</div>
<div class="pill">{contract['alerts']} captured alerts</div><div class="pill">${distance:.2f} from strike at snapshot</div>
<div class="muted">Last alert: {escape(contract['last'])} · {escape(contract['last_side'])} · {escape(contract['last_premium'])} premium<br>Option price at that alert: {escape(contract['last_price'])}. This is historical, not a current quote.</div></div>''',unsafe_allow_html=True)
                if contract.get('away') and contract.get('returned'):
                    with st.expander(f"Return evidence · {contract['contract']}"):
                        st.write(f"First captured contract alert: {contract['first']}")
                        st.write(f"Outside-zone SPY observation: {contract['away']}")
                        st.write(f"Subsequent inside-zone observation: {contract['returned']}")
                        st.caption('SPY observations come from all captured SPY alerts after the first alert for this contract. They are irregular samples, not a continuous price path. Short boundary crossings can qualify; no minimum excursion or dwell time has been validated. A later return is not proof of a winning trade.')
    with st.expander('Reading the board'):
        st.write('Calls and puts remain separate. An ask-side print is not proof of an opening directional trade. This board tracks observed price behavior and expiration; it does not estimate ITM odds or recommend an entry.')
        st.write('The initial capture covers only the displayed 250-row window. Older moves may be missing. Expired contracts are removed from active groups as the date advances. Private filter thresholds stay out of the site source and member explanations.')
    with st.expander('Admin / update snapshot'):
        if admin():
            uploaded=st.file_uploader('Upload classified Prestige snapshot JSON',type=['json'],key='prestige_upload')
            if uploaded and st.button('Load Prestige snapshot'):
                try:
                    incoming=json.load(uploaded)
                    for key in ['captured_at','source_time','coverage_start','spot','alert_count','cards']: assert key in incoming, f'Missing {key}'
                    for item in incoming['cards']:
                        for key in ['contract','type','expiry','status','strike','alerts','first','last','last_side','last_premium','last_price']: assert key in item, f'Missing {key}'
                        assert item['status'] in STATUSES
                        assert item['type'] in ['call','put']
                        datetime.strptime(item['expiry'],'%m/%d/%Y')
                    st.session_state.prestige_snapshot=incoming
                    st.rerun()
                except Exception as exc: st.error(f'Invalid snapshot: {exc}')
            st.download_button('Download Prestige snapshot',json.dumps(snapshot,indent=2),file_name='prestige.json',mime='application/json')
            st.caption('Session preview only. Replace data/prestige.json in GitHub to publish a reviewed snapshot. Automatic collection is not enabled.')
