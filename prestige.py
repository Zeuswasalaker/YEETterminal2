"""Evidence-backed Prestige snapshot display. No credentials or private filter settings."""
import json
from copy import deepcopy
from math import isfinite
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from urllib.parse import urlparse

STATUSES = ['Current Prestige','On Deck','Approaching','Watching','Expired']

def apply_lifecycle(snapshot, previous=None):
    """Require observed near -> farther OTM -> near, then retire observed ITM hits."""
    result=deepcopy(snapshot)
    observations=list((previous or {}).get('price_observations',[]))+list(result.get('price_observations',[]))
    if result.get('source_time') and result.get('spot'):
        observations.append({'time':result['source_time'],'spot':result['spot']})
    observations=sorted({(o['time'],float(o['spot'])):o for o in observations
                         if isfinite(float(o['spot'])) and float(o['spot'])>0}.values(),
                        key=lambda o:(o['time'],float(o['spot'])))
    result['price_observations']=observations
    prior_cards={c['contract']:c for c in (previous or {}).get('cards',[])}
    derived=('initial_near_at','away','returned','prestige_at','retired_at','retired_spot','retired_reason')
    for card in result.get('cards',[]):
        if card.get('classification_version')!='otm-sequence-v2':
            card.setdefault('classification_audit',[]).append({
                'reason':'Reclassified using observed near, farther OTM, return sequence; earlier labels are not verified outcomes.',
                'previous_status':card.get('status'),
                'previous_fields':{k:card[k] for k in derived if k in card}})
        saved_retirement={k:card[k] for k in ('retired_at','retired_spot','retired_reason') if k in card}
        prior=prior_cards.get(card['contract'],{})
        if prior.get('retired_at') and prior['retired_at']<saved_retirement.get('retired_at','9999'):
            saved_retirement={k:prior[k] for k in ('retired_at','retired_spot','retired_reason') if k in prior}
        for key in derived: card.pop(key,None)
        card['classification_version']='otm-sequence-v2'
        expiry=datetime.strptime(card['expiry'],'%m/%d/%Y').strftime('%Y/%m/%d')
        deadline=expiry+' 13:15:00'
        history=[o for o in observations if card['first']<=o['time']<=deadline]
        def otm(price):
            return (float(card['strike'])-price)/price if card['type']=='call' else (price-float(card['strike']))/price
        initial=None
        away=None
        activated=None
        for observation in history:
            stamp=observation['time']
            gap=otm(float(observation['spot']))
            if gap<0:
                card.update(retired_at=stamp,retired_spot=float(observation['spot']),
                            retired_reason=('Observed in the money after verified OTM comeback' if activated else 'Observed in the money after first captured alert; no verified Prestige outcome'))
                break
            if initial is None:
                if 0<=gap<=.005: initial=stamp
            elif away is None:
                if stamp>initial and gap>.005: away=stamp
            elif activated is None:
                if stamp>away and 0<=gap<=.005: activated=stamp
        if initial: card['initial_near_at']=initial
        if away: card['away']=away
        if activated:
            card['returned']=activated
            card['prestige_at']=activated
        last_time=result.get('source_time','')
        gap=otm(float(result['spot']))
        if saved_retirement.get('retired_at') and saved_retirement['retired_at']<card.get('retired_at','9999'):
            card.update(saved_retirement)
        if card.get('retired_at'):
            card['status']='Current Prestige' if activated else 'Watching'
        elif last_time>deadline:
            card['status']='Expired'
        elif gap<0:
            card['status']='Watching'
            card.update(retired_at=last_time,retired_spot=result['spot'],
                        retired_reason='Already ITM at latest observation; not a verified Prestige outcome')
        elif gap<=.005:
            card['status']='Current Prestige' if activated else 'On Deck'
        else:
            recent=[o for o in history if o['time']<=last_time]
            earlier=otm(float(recent[-4]['spot'])) if len(recent)>=4 else gap
            card['status']='Approaching' if gap<earlier else 'Watching'
    result['classification_version']='otm-sequence-v2'
    return result

def visible_cards(snapshot, today):
    cards=[]
    for original in apply_lifecycle(snapshot).get('cards',[]):
        if original.get('retired_at'): continue
        c=dict(original)
        if datetime.strptime(c['expiry'], '%m/%d/%Y').date()<today:
            continue
        cards.append(c)
    return cards


def prestige_performance(snapshot):
    """Count unique verified comebacks, including retired/expired history.

    An ITM touch after qualification and by the expiry cutoff is a hit,
    including extended hours. Open and unverified outcomes never enter the
    resolved hit-rate denominator. SPY options stop trading at 4:15 p.m. ET;
    timestamps in this snapshot are Pacific. No end-of-day price is invented.
    """
    snapshot=apply_lifecycle(snapshot)
    as_of=snapshot.get('source_time','')
    observations=snapshot.get('price_observations',[])
    qualified={}
    for card in snapshot.get('cards',[]):
        start=card.get('prestige_at')
        if not start or start>as_of:
            continue
        key=(card['type'],float(card['strike']),card['expiry'])
        if key not in qualified or start<qualified[key]['prestige_at']:
            qualified[key]=card
    rows=[]
    for card in qualified.values():
        start=card['prestige_at']
        deadline=datetime.strptime(card['expiry'],'%m/%d/%Y').strftime('%Y/%m/%d')+' 13:15:00'
        cutoff=min(as_of,deadline)
        history=sorted((o for o in observations if start<o['time']<=cutoff),key=lambda o:o['time'])
        def itm(price):
            return price>card['strike'] if card['type']=='call' else price<card['strike']
        hit=next((o for o in history if itm(float(o['spot']))),None)
        retired=card.get('retired_at','')
        if start<retired<=cutoff and card.get('retired_spot') is not None and itm(float(card['retired_spot'])):
            if hit is None or retired<hit['time']:
                hit={'time':retired,'spot':card['retired_spot']}
        evidence=hit
        if hit:
            outcome='ITM hit'
        elif as_of<deadline:
            outcome='Open'
        else:
            # Accept the completed final-minute close or an exact cutoff check.
            closing=[o for o in history if o['time']>=deadline[:11]+'13:14:59']
            evidence=closing[-1] if closing else None
            if evidence and float(evidence['spot'])!=float(card['strike']):
                outcome='Expired OTM'
            else:
                outcome='Outcome unverified'
        rows.append({'contract':card['contract'],'qualified_at':start,'expiry':card['expiry'],'unexpired':as_of<deadline,
                     'outcome':outcome,'observed_at':evidence['time'] if evidence else '',
                     'observed_spot':float(evidence['spot']) if evidence else None})
    wins=sum(r['outcome']=='ITM hit' for r in rows)
    losses=sum(r['outcome']=='Expired OTM' for r in rows)
    return {'total':len(rows),'itm':wins,'expired_otm':losses,
            'open':sum(r['outcome']=='Open' for r in rows),
            'plays_open':sum(r['unexpired'] for r in rows),
            'open_itm_hits':sum(r['unexpired'] and r['outcome']=='ITM hit' for r in rows),
            'unverified':sum(r['outcome']=='Outcome unverified' for r in rows),
            'win_percent':100*wins/(wins+losses) if wins+losses else None,
            'records':sorted(rows,key=lambda r:(r['qualified_at'],r['contract']))}

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
    with st.container(key='milt_prestige') , st.expander('milt stuff'):
        if admin():
            uploaded=st.file_uploader('Saved Prestige data (.json)',type=['json'],key='prestige_upload')
            if uploaded and st.button('Show these contracts',type='primary'):
                try:
                    incoming=apply_lifecycle(validate_snapshot(json.load(uploaded)),snapshot)
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
    option_kind=contract['type']
    strike=f"{float(contract['strike']):g}"
    side='CALL' if contract['type']=='call' else 'PUT'
    icon='📞' if side=='CALL' else '🩸'
    expiry=datetime.strptime(contract['expiry'],'%m/%d/%Y').strftime('%b %d, %Y')
    status=escape({'Current Prestige':'Current Prestige','On Deck':'On deck','Approaching':'Getting closer','Watching':'Still watching','Expired':'Expired'}.get(contract['status'],contract['status']))
    try:
        first=datetime.strptime(contract['first'],'%Y/%m/%d %H:%M:%S').strftime('%b %d, %Y · %I:%M:%S %p')
    except (KeyError,ValueError,TypeError):
        first='Not recorded'
    return f'<article class="gold-contract gold-{option_kind}" aria-label="SPY {strike} {side} expiring {expiry}"><div class="gold-top"><span>{icon} {side}</span><span>{symbol}</span></div><div class="gold-strike">{strike}<span>{"c" if side=="CALL" else "p"}</span></div><div class="gold-expiry">Expires {expiry}</div><div class="gold-status">{status}</div><div class="gold-first"><span>First spotted</span><strong>{escape(first)}</strong><small>First appearance in our saved alerts</small></div><div class="gold-foot">{contract["alerts"]} saved alerts · ${abs(float(contract["strike"])-spot):.2f} from strike<br>At the saved SPY price</div></article>'


def render(admin):
    import streamlit as st
    # Check for newly published snapshots without requiring a browser reload.
    st.fragment(run_every='30s')(_render)(admin)

def _render(admin):
    import streamlit as st
    path=Path(__file__).parent/'data'/'prestige.json'
    version=path.stat().st_mtime_ns if path.exists() else None
    if 'prestige_snapshot' not in st.session_state or st.session_state.get('prestige_file_version')!=version:
        st.session_state.prestige_file_version=version
        try:
            private=st.secrets.get('PRESTIGE_SNAPSHOT_JSON','')
        except Exception:
            private=''
        try:
            initial=json.loads(private) if private else json.loads(path.read_text())
            st.session_state.prestige_snapshot=apply_lifecycle(validate_snapshot(initial),st.session_state.get('prestige_snapshot'))
        except Exception:
            st.error('Prestige is temporarily unavailable.')
            st.session_state.prestige_snapshot={'cards':[]}
    snapshot=apply_lifecycle(st.session_state.prestige_snapshot)
    st.session_state.prestige_snapshot=snapshot
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
.prestige-stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:24px 0}
.prestige-stat{padding:17px;border-radius:16px;border:1px solid #a9bd8d33;background:#1a3737;color:#bdcfc5;font:700 12px/1.6 "Trebuchet MS",Arial,sans-serif}
.prestige-stat strong{display:block;font:900 32px/1.4 "Trebuchet MS",Arial,sans-serif;color:#ead18e}
.prestige-stat:nth-child(2){background:#193c31;border-color:#8bbf8366}.prestige-stat:nth-child(2) strong{color:#b9e59b}
.prestige-stat:nth-child(3){background:#422e2b;border-color:#d99d8d66}.prestige-stat:nth-child(3) strong{color:#ffc0aa}
.prestige-stat:nth-child(4){background:#3c3926;border-color:#dfc27c88}
@media(min-width:641px) and (max-width:1000px){.prestige-stats{grid-template-columns:repeat(3,minmax(0,1fr))}}
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

.prestige-hero{padding:0!important;margin:0 0 8px!important}
.prestige-hero h1{margin:0!important;padding-bottom:8px!important}
.bricks-heading{font:800 24px/1.4 "Trebuchet MS",Arial,sans-serif;color:#edd18d;margin:13px 0 8px}
.gold-grid{grid-template-columns:repeat(3,minmax(0,300px));gap:20px;margin:10px 0 22px}
.gold-contract{padding:20px}
.gold-strike{font-size:46px;margin-top:12px}
.board-counts{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 16px}
.board-counts span{padding:8px 13px;border:1px solid #d4c18444;background:#203b35;border-radius:10px;color:#dce6d0;font:600 12px/1.5 "Trebuchet MS",Arial,sans-serif}
.board-counts strong{color:#f0d68e;margin-left:7px}
@media(max-width:900px){.gold-grid{grid-template-columns:repeat(2,minmax(0,300px))}}
@media(max-width:480px){.gold-grid{grid-template-columns:1fr;max-width:300px}}

@media(forced-colors:active){.gold-contract{background:Canvas;color:CanvasText;border:2px solid CanvasText;box-shadow:none}.gold-contract *{color:CanvasText;text-shadow:none}}
</style>''',unsafe_allow_html=True)
    st.markdown('<div class="prestige-hero"><h1>The Prestige</h1></div>',unsafe_allow_html=True)

    stats=prestige_performance(snapshot)
    try:
        audit=json.loads((Path(__file__).parent/'data/prestige_audit.json').read_text())
    except (OSError,ValueError):
        audit={'records':[],'scope':'Publication audit unavailable; historical sequences remain reconstructed.'}
    evidence={r['contract']:r for r in audit.get('records',[])}
    for row in stats['records']:
        row.update({k:evidence.get(row['contract'],{}).get(k,'') for k in ('provenance','published_at','source_url')})
        row['provenance']=row['provenance'] or 'Reconstructed from saved observations'
    published=[r for r in stats['records'] if r['published_at']]
    wins=sum(r['outcome']=='ITM hit' for r in published)
    losses=sum(r['outcome']=='Expired OTM' for r in published)
    current={c['contract'] for c in cards if c['status']=='Current Prestige'}
    earlier=[r for r in published if r['unexpired'] and r['contract'] not in current
             and datetime.strptime(r['expiry'],'%m/%d/%Y').date()>=today]
    rate=f'{100*wins/(wins+losses):.1f}%' if wins+losses else '—'
    metrics=[('🥇 Current setups',str(len(current))),('👀 Still Open',str(len(earlier))),
             ('✅ Completed ITM hits',str(wins)),('⌛ Expired OTM',str(losses)),('🎯 Published-cohort ITM rate',rate)]
    st.markdown('<div class="prestige-stats">'+''.join(
        '<div class="prestige-stat">'+escape(label)+'<strong>'+escape(value)+'</strong></div>'
        for label,value in metrics)+'</div>',unsafe_allow_html=True)
    st.caption(f"Published cohort: {len(published)} unique contracts · {sum(r['outcome']=='Outcome unverified' for r in published)} expired outcomes unverified · Price checks through {snapshot.get('source_time','unknown')} Pacific")
    st.caption('Current setups qualify on the latest board. Still Open retains previously published, unexpired plays outside the current setup board, including contracts already recorded ITM. An ITM hit stays marked as a completed result while the contract remains unexpired. These lists do not represent actual subscriber positions.')
    st.caption('Premarket and after-hours ITM checks count after qualification and before expiration. The ITM rate is hits ÷ (hits + verified OTM expirations); unresolved outcomes are excluded. Repository publication is documented, but this is not a continuous live track record or an option-profit rate.')
    if st.button(f'👀 Still Open ({len(earlier)})  ' + ('▲ Hide cards' if st.session_state.get('prestige_still_open_visible',False) else '▼ Show cards'), key='prestige_still_open_toggle', use_container_width=True):
        st.session_state.prestige_still_open_visible=not st.session_state.get('prestige_still_open_visible',False)
    if st.session_state.get('prestige_still_open_visible',False):
        if earlier:
            tiles=[]
            for row in sorted(earlier,key=lambda r:(datetime.strptime(r['expiry'],'%m/%d/%Y'),r['contract'])):
                contract=row['contract']
                expiry=datetime.strptime(row['expiry'],'%m/%d/%Y').strftime('%b %d, %Y')
                hit=row['outcome']=='ITM hit'
                result='✅ ITM HIT' if hit else ('⏳ AWAITING RESULT' if row['outcome']=='Open' else row['outcome'])
                observed=('ITM checked: '+row['observed_at']+' PT') if hit and row['observed_at'] else 'No confirmed ITM check yet'
                tiles.append(
                    '<article class="gold-contract" style="min-height:210px">'
                    '<div class="gold-top"><span>👀 STILL OPEN</span><span>$SPY</span></div>'
                    '<div class="gold-strike" style="font-size:32px">'+escape(contract)+'</div>'
                    '<div class="gold-expiry">Expires '+escape(expiry)+'</div>'
                    '<div class="gold-status">'+escape(result)+'</div>'
                    '<div class="gold-first"><span>'+escape(observed)+'</span>'
                    '<small>Published: '+escape(row['published_at'] or 'Not recorded')+' PT</small>'
                    '<small>Prestige qualified: '+escape(row['qualified_at'])+' PT</small></div>'
                    '</article>')
            st.markdown('<div class="gold-grid">'+''.join(tiles)+'</div>',unsafe_allow_html=True)
        else:
            st.info('No previously published carryover plays remain unexpired in this saved update.')
    with st.expander('✅ Completed published ITM hits, including unexpired contracts'):
        st.dataframe([{'Contract':r['contract'],'Expires':datetime.strptime(r['expiry'],'%m/%d/%Y').date(),
                       'Published (PT)':r['published_at'],'ITM check (PT)':r['observed_at'],
                       'SPY at hit':r['observed_spot']} for r in published if r['outcome']=='ITM hit'],hide_index=True,use_container_width=True)
    with st.expander('📊 Full reconstructed history and publication audit'):
        st.write(f"{stats['total']} observed comeback sequences in saved history: {len(published)} have publication evidence before outcome; {stats['total']-len(published)} are reconstructed or lack that evidence. The former 93.3% figure pooled these groups and is not a live track record.")
        st.write(audit.get('scope',''))
        st.caption('A hit requires a saved price crossing after qualification, by the 4:15 p.m. Eastern SPY options cutoff. Expired OTM requires a saved final-minute closing check and no recorded ITM hit. Missing closing evidence remains unverified. Sparse history and minute closes can miss brief crosses; no tested future winning odds are claimed.')
        st.dataframe([{'Contract':r['contract'],'Provenance':r['provenance'],'Published (PT)':r['published_at'],
                       'Publication source':r['source_url'],'Became Prestige (PT)':r['qualified_at'],'Result':r['outcome'],
                       'Result check (PT)':r['observed_at'],'SPY at result':r['observed_spot']} for r in stats['records']],
                     hide_index=True,use_container_width=True)

    if not snapshot.get('cards'):
        st.info('No contracts to show in this update.')
        admin_upload(admin,snapshot)
        return
    try:
        saved_date=datetime.fromisoformat(snapshot['captured_at'].replace('Z','+00:00')).astimezone(ZoneInfo('America/Los_Angeles')).strftime('%b %d, %Y')
    except ValueError:
        saved_date='the date below'
    st.caption(f'Latest SPY price check: {snapshot["source_time"]} · SPY ${snapshot["spot"]:.2f} · Refreshed snapshot, not a streaming feed')
    st.caption('Once a Prestige contract moves in the money in a saved price check, it leaves every board. The page checks for published updates every 30 seconds.')
    with st.container(key='prestige_controls'), st.expander('Filter the bricks'):
        side=st.pills('What are we watching?',['🎩 Everything','📞 Calls','🩸 Puts'],default='🎩 Everything',selection_mode='single') or '🎩 Everything'
        boards=['🥇 Current Prestige','👀 On deck','🧲 Getting closer','📦 Still watching']
        board=st.pills('Pick a board',boards,default=boards[0],selection_mode='single') or boards[0]
    i=boards.index(board)
    descriptions=[
        'SPY moved away and came back near the strike in our saved observations. It was still nearby at the last check. That’s the sequence we’re looking for.',
        'Close to the strike, but no full comeback is established in this saved window. Next up: watch for the move away and return before expiration.',
        'SPY was outside the nearby area but moving closer across our last few observations. Watch for it to come back in. The earlier move-away story still matters.',
        'These contracts need another look. Watch for a fresh approach and return before expiration.'
    ]
    st.markdown(f'<div class="bricks-heading">{boards[i]}</div>',unsafe_allow_html=True)
    wanted=[STATUSES[i]] if i<3 else ['Watching']
    selected=[x for x in cards if x['status'] in wanted and (side=='🎩 Everything' or x['type']==('call' if side=='📞 Calls' else 'put'))]
    selected.sort(key=lambda x:(datetime.strptime(x['expiry'],'%m/%d/%Y'),abs(x['strike']-snapshot['spot'])))

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
    st.markdown('<div class="bricks-heading">📋 The whole board</div>',unsafe_allow_html=True)
    st.caption('Every contract still on watch. Prestige contracts already observed in the money are removed. Statuses describe the saved update above.')
    status_labels={'Current Prestige':'🥇 Current Prestige','On Deck':'👀 On deck','Approaching':'🧲 Getting closer','Watching':'📦 Still watching','Expired':'⌛ Expired'}
    counts={status:sum(c['status']==status for c in cards) for status in STATUSES}
    chips=''.join(f'<span>{status_labels[state]} <strong>{counts[state]}</strong></span>' for state in STATUSES if counts[state])
    st.markdown('<div class="board-counts">'+chips+'</div>',unsafe_allow_html=True)
    import pandas as pd
    whole=sorted(cards,key=lambda x:(STATUSES.index(x['status']),datetime.strptime(x['expiry'],'%m/%d/%Y'),x['strike']))
    rows=[{'Contract':f'$SPY {item["strike"]:g}{"c" if item["type"]=="call" else "p"}',
           'Status':status_labels[item['status']],
           'Type':'📞 Call' if item['type']=='call' else '🩸 Put',
           'Expires':datetime.strptime(item['expiry'],'%m/%d/%Y').date(),
           'First spotted (UW clock)':item['first'],
           'Saved alerts':item['alerts'],
           'Last alert premium':item['last_premium']} for item in whole]
    st.dataframe(pd.DataFrame(rows),hide_index=True,width='stretch',height=min(760,36*len(rows)+40))
    st.caption('First spotted = earliest alert in our saved window. Premium = the last saved alert amount, not a total.')
    with st.expander('🎩 What is The Prestige?'):
        st.markdown('''<section class="prestige-how"><h3>The comeback is the point. 🪃</h3><p>In our research, contracts that <strong>move away from their strike and come back before expiration</strong> have been higher-percentage setups. That’s <strong>The Prestige</strong>, and that’s what we’re tracking here.</p><div class="prestige-issue">The running tally counts observed results in our saved history. It does not establish future winning odds.</div></section>''',unsafe_allow_html=True)
        st.write(descriptions[i])
        st.caption('📞 Green = calls · 🩸 Red = puts. An alert alone does not tell us the trader’s complete plan.')
        try:
            issue_url=snapshot.get('issue_url') or st.secrets.get('PRESTIGE_ISSUE_URL','')
        except Exception:
            issue_url=snapshot.get('issue_url','')
        if issue_url and urlparse(issue_url).scheme=='https' and urlparse(issue_url).netloc:
            st.link_button('📰 Read the YEET behind this board',issue_url)
    with st.expander('📌 When was this checked?'):
        st.write(f"Board captured: {snapshot['captured_at']}. Source alerts: {snapshot['coverage_start']} through {snapshot.get('latest_alert_time',snapshot['source_time'])}. Price check: {snapshot['source_time']}.")
        st.write('First spotted is the earliest appearance across our saved captures, not necessarily the first-ever appearance. Alert counts include retained captures, deduplicated by contract and alert timestamp. Source timezone: '+snapshot.get('source_timezone','not verified')+'.')
        st.write(f"{snapshot['alert_count']} saved alert rows · {len(cards)} contracts still on the board. Alerts are not verified unique trades or individual whales. Premium amounts are rounded source labels.")
        st.write('In the money means SPY is above a call strike or below a put strike. A recorded crossing retires that Prestige contract even if SPY later reverses. Reaching the strike does not establish an option profit; entry premium and execution still matter. Crossings between saved price checks may be missed.')
        st.write(snapshot.get('coverage_note','Prices are saved observations; crossings between checks may be missed.'))
        st.write('Premarket and after-hours SPY crossings count toward retirement even while options are closed. A strike crossing does not establish an executable option profit. Comeback sequences and ITM retirement use saved prices and minute closes; brief intraminute crossings can be missed. This is a research board, not tested winning odds.')
    admin_upload(admin,snapshot)
