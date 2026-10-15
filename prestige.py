"""Evidence-backed Prestige snapshot display. No credentials or private filter settings."""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from urllib.parse import urlparse

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
            with st.form('prestige_issue_link'):
                issue_link=st.text_input('Link to the YEET issue for this board',value=snapshot.get('issue_url',''),placeholder='https://…')
                save_issue=st.form_submit_button('Attach the YEET issue')
            if save_issue:
                parsed=urlparse(issue_link)
                if issue_link and (parsed.scheme!='https' or not parsed.netloc):
                    st.error('Use the full HTTPS link to the issue.')
                else:
                    snapshot['issue_url']=issue_link
                    st.session_state.prestige_snapshot=snapshot
                    st.rerun()
            st.download_button('Download saved contracts',json.dumps(snapshot,indent=2),file_name='prestige.json',mime='application/json')
            st.caption('Uploads preview contracts in your session. For a shared board without committing data to GitHub, set PRESTIGE_SNAPSHOT_JSON in Streamlit Secrets to the snapshot JSON string. Neither method starts automatic collection.')


def gold_tile(contract,spot):
    symbol='$SPY'
    strike=f"{float(contract['strike']):g}"
    side='CALL' if contract['type']=='call' else 'PUT'
    icon='📞' if side=='CALL' else '🩸'
    expiry=datetime.strptime(contract['expiry'],'%m/%d/%Y').strftime('%b %d, %Y')
    status=escape({'Current Prestige':'The comeback','On Deck':'On deck','Approaching':'Getting closer','Watching':'Still watching','Expired':'Expired'}.get(contract['status'],contract['status']))
    try:
        first=datetime.strptime(contract['first'],'%Y/%m/%d %H:%M:%S').strftime('%b %d, %Y · %I:%M:%S %p')
    except (KeyError,ValueError,TypeError):
        first='Not recorded'
    return f'<article class="gold-contract gold-{contract['type']}" aria-label="SPY {strike} {side} expiring {expiry}"><div class="gold-top"><span>{icon} {side}</span><span>{symbol}</span></div><div class="gold-strike">{strike}<span>{"c" if side=="CALL" else "p"}</span></div><div class="gold-expiry">Expires {expiry}</div><div class="gold-status">{status}</div><div class="gold-first"><span>First spotted</span><strong>{escape(first)}</strong><small>First appearance in our saved alerts</small></div><div class="gold-foot">{contract["alerts"]} saved alerts · ${abs(float(contract["strike"])-spot):.2f} from strike<br>At the saved SPY price</div></article>'


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

.gold-call{background:linear-gradient(128deg,#f4edb0 0%,#c6b74f 24%,#e3d789 45%,#87964b 75%,#d9ce75 100%);border-color:#b9df80;box-shadow:inset 2px 2px 1px #fff7ce,inset -3px -4px 2px #647335,0 7px 0 #435626,0 13px 20px #0005}
.gold-put{background:linear-gradient(128deg,#ffe5a9 0%,#d8a05b 24%,#edc385 45%,#b8785e 75%,#dfb46d 100%);border-color:#e6a38c;box-shadow:inset 2px 2px 1px #fff0c4,inset -3px -4px 2px #8d4f37,0 7px 0 #703e30,0 13px 20px #0005}
.prestige-hero{padding:12px 0 18px}.prestige-kicker{font:800 11px/1.5 "Trebuchet MS",Arial,sans-serif;letter-spacing:.16em;color:#e8c875}
.prestige-hero h1{font-family:"Arial Rounded MT Bold","Trebuchet MS",Arial,sans-serif!important;background:none!important;-webkit-text-fill-color:#f0d384!important;color:#f0d384!important;text-shadow:1px 2px 0 #8a642a,3px 5px 0 #081c24;letter-spacing:-.045em}
.prestige-tagline{font:700 18px/1.6 "Trebuchet MS",Arial,sans-serif;color:#d9e6d5}
.prestige-how{background:linear-gradient(135deg,#25443d,#153238);border:1px solid #d3c18a55;border-radius:22px;padding:26px;margin:14px 0 20px;box-shadow:0 5px 0 #081f27}
.prestige-how h3{font:800 25px/1.3 "Trebuchet MS",Arial,sans-serif!important;color:#f0d384!important;margin:0 0 12px}
.prestige-how p{font:500 16px/1.75 "Trebuchet MS",Arial,sans-serif;color:#bdd7c9;max-width:850px}
.prestige-how strong{color:#f3e6b4}.prestige-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:20px}
.prestige-step{padding:17px;background:#0e292d;border-radius:14px;border:1px solid #98b69a33;font:500 14px/1.6 "Trebuchet MS",Arial,sans-serif;color:#b9d0c7}
.prestige-step b{display:block;font-size:16px;color:#e9cf8d;margin-bottom:7px}
.prestige-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0}
.prestige-stat{padding:17px;border-radius:16px;border:1px solid #a9bd8d33;background:#1a3737;color:#bdcfc5;font:700 12px/1.6 "Trebuchet MS",Arial,sans-serif}
.prestige-stat strong{display:block;font:900 32px/1.4 "Trebuchet MS",Arial,sans-serif;color:#ead18e}
.prestige-saved{background:#263c30;border:1px solid #9eb27744;border-radius:12px;padding:13px 18px;color:#c8d7b8;font:500 13px/1.6 "Trebuchet MS",Arial,sans-serif}
.prestige-board{margin:12px 0 4px;padding:22px 24px;border:2px solid #7b745055;border-radius:20px;background:linear-gradient(135deg,#253c35,#152f32);box-shadow:inset 0 1px 0 #d3c58422,0 4px 0 #0b2027}
.prestige-board h3{color:#edcf88!important;font:800 25px/1.4 "Trebuchet MS",Arial,sans-serif!important;margin:0 0 8px}
.prestige-board p{color:#c4d7cd;font:500 15px/1.7 "Trebuchet MS",Arial,sans-serif;margin:0}
.prestige-issue{border-left:4px solid #dfc27c;padding:14px 18px;background:#243b3488;border-radius:0 12px 12px 0;color:#bdd4c7;margin-top:18px;font:500 14px/1.7 "Trebuchet MS",Arial,sans-serif}
.st-key-prestige_controls [data-testid="stBaseButton-pills"]{border-radius:12px!important;background:#24453d!important;color:#e6dfbb!important;border:1px solid #c2c78b55!important;box-shadow:0 3px 0 #071e24!important;font-weight:750!important;padding:10px 16px!important}
.st-key-prestige_controls [aria-pressed="true"]{background:linear-gradient(135deg,#f1d692,#c7a652)!important;color:#312713!important;border-color:#ead08d!important}
@media(max-width:640px){.prestige-steps{grid-template-columns:1fr}.prestige-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.prestige-how{padding:21px}.prestige-board{padding:19px}}
@media(max-width:900px){.gold-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.gold-strike{font-size:46px}}
@media(max-width:480px){.gold-grid{grid-template-columns:1fr;gap:22px;max-width:340px;margin-left:auto;margin-right:auto}.gold-strike{font-size:58px}}
@media(forced-colors:active){.gold-contract{background:Canvas;color:CanvasText;border:2px solid CanvasText;box-shadow:none}.gold-contract *{color:CanvasText;text-shadow:none}}
</style>''',unsafe_allow_html=True)
    st.markdown('<div class="prestige-hero"><div class="prestige-kicker">THE YEET / THE GOLD-BRICK WATCHLIST</div><h1>The Prestige</h1><div class="prestige-tagline">Everybody loves a comeback. We’re watching for one.</div></div>',unsafe_allow_html=True)
    st.markdown('''<section class="prestige-how"><h3>The comeback is the point. 🪃</h3><p>In our research, contracts that <strong>move away from their strike and come back before expiration</strong> have been higher-percentage setups. That’s <strong>The Prestige</strong>, and that’s what we’re tracking here.</p><div class="prestige-issue">Our research finding, not a guarantee. No verified win rate is displayed on this board.</div></section>''',unsafe_allow_html=True)
    try:
        issue_url=snapshot.get('issue_url') or st.secrets.get('PRESTIGE_ISSUE_URL','')
    except Exception:
        issue_url=snapshot.get('issue_url','')
    if issue_url and urlparse(issue_url).scheme=='https' and urlparse(issue_url).netloc:
        st.link_button('📰 Read the YEET behind this board',issue_url)
    if not snapshot.get('cards'):
        st.info('The board is ready. Load saved contracts in Milt’s controls to put some bricks on it.')
        admin_upload(admin,snapshot)
        return
    try:
        saved_date=datetime.fromisoformat(snapshot['captured_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles')).strftime('%b %d, %Y')
    except ValueError:
        saved_date='the date below'
    st.markdown(f'<div class="prestige-saved">📌 <strong>Saved board · {escape(saved_date)}</strong> · SPY ${snapshot["spot"]:.2f} at the last saved alert. These are saved observations, not live prices.</div>',unsafe_allow_html=True)
    counts={status:sum(c['status']==status for c in cards) for status in STATUSES}
    st.markdown(f'<div class="prestige-stats"><div class="prestige-stat">🥇 Came back<strong>{counts["Current Prestige"]}</strong></div><div class="prestige-stat">👀 On deck<strong>{counts["On Deck"]}</strong></div><div class="prestige-stat">🧲 Getting closer<strong>{counts["Approaching"]}</strong></div><div class="prestige-stat">🐋 Contracts tracked<strong>{len(cards)}</strong></div></div>',unsafe_allow_html=True)
    with st.container(key='prestige_controls'):
        side=st.pills('What are we watching?',['🎩 Everything','📞 Calls','🩸 Puts'],default='🎩 Everything',selection_mode='single') or '🎩 Everything'
        boards=['🥇 The comebacks','👀 On deck','🧲 Getting closer','📦 Still watching']
        board=st.pills('Pick a board',boards,default=boards[0],selection_mode='single') or boards[0]
    i=boards.index(board)
    descriptions=[
        'SPY moved away and came back near the strike in our saved observations. It was still nearby at the last check. That’s the sequence we’re looking for.',
        'Close to the strike, but no full comeback is established in this saved window. Next up: watch for the move away and return before expiration.',
        'SPY was outside the nearby area but moving closer across our last few observations. Watch for it to come back in. The earlier move-away story still matters.',
        'These contracts need another look, or have already expired. An active one needs a fresh approach and return before its deadline.'
    ]
    st.markdown(f'<section class="prestige-board"><h3>{boards[i]}</h3><p>{descriptions[i]}</p></section>',unsafe_allow_html=True)
    wanted=[STATUSES[i]] if i<3 else ['Watching','Expired']
    selected=[x for x in cards if x['status'] in wanted and (side=='🎩 Everything' or x['type']==('call' if side=='📞 Calls' else 'put'))]
    selected.sort(key=lambda x:(datetime.strptime(x['expiry'],'%m/%d/%Y'),abs(x['strike']-snapshot['spot'])))
    st.caption('📞 Green tint = calls · 🩸 Red tint = puts. Calls are often used for an upside bet; puts for a downside bet or protection. We can’t see the trader’s full plan from an alert.')
    if not selected:
        st.info('No bricks on this board for that choice. Try Everything or another board.')
    else:
        st.markdown('<div class="gold-grid">'+''.join(gold_tile(item,snapshot['spot']) for item in selected)+'</div>',unsafe_allow_html=True)
        with st.expander('🔎 Take a closer look at a contract'):
            chosen=st.selectbox('Which contract?',[item['contract'] for item in selected],key=f'prestige_details_{i}')
            contract=next(item for item in selected if item['contract']==chosen)
            st.write(f"First saved appearance: {contract['first']}")
            st.write(f"Last saved alert: {contract['last']} · {contract['last_side']} · {contract['last_premium']} option premium")
            st.write(f"Option price at that alert: {contract['last_price']}. This is a past price, not a quote for buying now.")
            if contract.get('away') and contract.get('returned'):
                st.write(f"👋 Away from the strike area: {contract['away']}")
                st.write(f"🪃 Back near the strike: {contract['returned']}")
            else:
                st.caption('We don’t have a full move-away-and-return sequence established for this contract in the saved data.')
    with st.expander('📌 When was this checked?'):
        st.write(f"Board captured: {snapshot['captured_at']}. Source alerts: {snapshot['coverage_start']} through {snapshot['source_time']}.")
        st.write('First spotted is the earliest alert in our saved window, not necessarily the first-ever appearance. UW’s displayed clock timezone has not been verified.')
        st.write(f"{snapshot['alert_count']} saved alert rows, grouped into {len(cards)} contracts. Alerts are not verified unique trades or individual whales. Premium amounts are rounded source labels.")
        st.write('SPY prices here come from irregular alert observations. We haven’t filled in a complete intraday history. A brief boundary crossing can qualify; no minimum time away or excursion has been validated. This is a research board, not tested winning odds.')
    admin_upload(admin,snapshot)
