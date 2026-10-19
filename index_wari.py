"""Index WARI: baseline-relative disagreement between flow and price."""
from pathlib import Path
from math import exp
import json
import re
import html
import pandas as pd
import streamlit as st
from wari import prepare

ROOT = Path(__file__).parent
PRICE_LOOKBACK = 60
MIN_PRICE_SESSIONS = 20
DIVERGENCE_SCALE = 0.6

def divergence(call_share, baseline_share, share_std, index_return, return_std):
    if return_std <= 0:
        raise ValueError('Historical index volatility must be positive.')
    flow_z = 2 * call_share - 1
    price_z = index_return / return_std
    conflict = max(0.0, -flow_z * price_z)
    value = 100 * (1 - exp(-conflict / DIVERGENCE_SCALE))
    direction = 'Bullish whale / falling index' if flow_z > 0 and price_z < 0 else 'Bearish whale / rising index' if flow_z < 0 and price_z > 0 else 'No opposing signal'
    level = 'Extreme disagreement' if value >= 75 else 'Strong disagreement' if value >= 50 else 'Noticeable disagreement' if value >= 25 else 'Little disagreement'
    return value, level, direction, flow_z, price_z

def daily_flow(raw):
    frame, _ = prepare(raw)
    frame = frame.loc[frame.ticker.eq('SPY')]
    rows=[]
    for day, group in frame.groupby('date'):
        total=group.premium.sum()
        rows.append({'date':pd.Timestamp(day),'call_share':group.loc[group.type.eq('call'),'premium'].sum()/total,'prints':len(group),'premium':total})
    return pd.DataFrame(rows).set_index('date').sort_index() if rows else pd.DataFrame()

def historical_scores(flow, prices, window=PRICE_LOOKBACK, minimum=MIN_PRICE_SESSIONS):
    close=pd.to_numeric(prices, errors='coerce').dropna().sort_index()
    close.index=pd.to_datetime(close.index).tz_localize(None).normalize()
    close=close[~close.index.duplicated(keep='last')]
    returns=close.pct_change(fill_method=None)
    out=flow.join(returns.rename('return'),how='left')
    # All baselines end before the signal date. Missing sessions are not zero flow.
    out['flow_mean']=0.5
    out['flow_std']=1.0
    out['price_std']=returns.shift(1).rolling(window,min_periods=minimum).std().reindex(out.index)
    for day,row in out.iterrows():
        fields=['call_share','flow_mean','flow_std','return','price_std']
        if row[fields].notna().all() and row.flow_std>0 and row.price_std>0:
            result=divergence(row.call_share,row.flow_mean,row.flow_std,row['return'],row.price_std)
            out.loc[day,'Index WARI']=result[0]
    return out

def hero(value=None, level='SPY Magic / index update pending', detail='The score compares SPY Magic whale direction with the index move. A matched reading is not currently connected; historical flow is not required.', direction=''):
    accent = '#b9ef76' if direction.startswith('Bullish') else '#ff9b9b' if direction.startswith('Bearish') else '#efd58a'
    background = '#214b3a,#122e36' if direction.startswith('Bullish') else '#572f38,#242d38' if direction.startswith('Bearish') else '#49412d,#172f36'
    number='—' if value is None else f'{value:.0f}<span style="font-size:22px"> / 100</span>'
    position = 0 if value is None else max(0, min(100, value))
    pointer = '' if value is None else f'<span style="position:absolute;left:{position}%;top:-12px;transform:translateX(-50%);font-size:26px;color:#fff">▼</span>'
    scale = f'<div role="img" aria-label="Divergence scale, {value if value is not None else "unavailable"} out of 100" style="position:relative;height:20px;border-radius:12px;background:linear-gradient(90deg,#398a73,#e8c66c,#e17c49,#b84062);margin:22px 12px 8px">{pointer}</div><div style="display:flex;justify-content:space-between;font-size:12px;color:#d5dfcb"><span>0 · little</span><span>50 · strong</span><span>100 · extreme</span></div>'
    st.markdown(f'<div style="padding:26px;border-radius:24px;background:linear-gradient(120deg,{background});border:1px solid #b9ef7666;box-shadow:0 6px 0 #071d24;margin-bottom:24px"><div style="color:#b9ef76;font-weight:900;letter-spacing:.12em">INDEX WARI · WHALE / PRICE DIVERGENCE</div><div style="font-size:64px;font-weight:900;color:#efd58a;line-height:1.2">{number}</div><div style="font-size:25px;font-weight:800;color:{accent}">{html.escape(level)}</div><p style="font-size:17px;color:#e2ebd4">{html.escape(direction)}</p><p style="color:#c0d3c8">{html.escape(detail)}</p>{scale}</div>',unsafe_allow_html=True)

def render():
    top=st.empty()
    with top.container(): hero()
    st.caption('Whale Alert Risk Indicator · SPY Magic versus SPY price')
    flow_path=ROOT/'data/spy_magic_flow.csv'
    price_path=ROOT/'data/wari_prices.csv'
    raw=None
    has_reading=False
    if flow_path.exists():
        try: raw=pd.read_csv(flow_path)
        except (ValueError,OSError): pass
    prices=None
    if price_path.exists():
        try:
            p=pd.read_csv(price_path)
            p.columns=[str(c).lower().strip() for c in p.columns]
            if 'ticker' in p: p=p.loc[p.ticker.str.upper().eq('SPY')]
            prices=pd.Series(pd.to_numeric(p['close']).values,index=pd.to_datetime(p['date']))
        except (ValueError,KeyError): st.caption('Price reference could not be validated.')
    if raw is not None:
        try:
            flow=daily_flow(raw)
            if not flow.empty and prices is not None:
                results=historical_scores(flow,prices)
                usable=results.dropna(subset=['Index WARI']) if 'Index WARI' in results else pd.DataFrame()
                if not usable.empty:
                    day=usable.index[-1]
                    row=usable.loc[day]
                    v,level,direction,fz,pz=divergence(row.call_share,row.flow_mean,row.flow_std,row['return'],row.price_std)
                    detail=f'{day.date()}: calls received {row.call_share:.0%} of observed premium. SPY moved {row["return"]:+.2%}, or {pz:+.1f} times its usual daily volatility. The score rises when whale direction and index price pull in opposite directions.'
                    with top.container(): hero(v,level,detail,direction)
                    has_reading=True
                    st.line_chart(usable[['Index WARI']],color='#b9ef76')
                    st.caption('Price baseline: prior 60 index returns, minimum 20. Flow and price must cover the same completed session.')
                else: st.info('A matched flow session and at least 20 prior index returns with nonzero volatility are needed.')
        except (ValueError,KeyError,TypeError) as exc: st.error(str(exc))
    if not has_reading:
        render_saved_snapshot(top)
    render_broad_comparison(top)
    st.markdown('### Read it in ten seconds')
    a,b,c=st.columns(3)
    for col,title,copy,color in [
        (a,'📞 Bullish disagreement','Whales lean toward calls while SPY falls. Watch for a bounce confirmation.','#274f3b'),
        (b,'🩸 Bearish disagreement','Whales lean toward puts while SPY rises. Watch for the rally to weaken.','#56313c'),
        (c,'🔀 Mixed / aligned','No clear opposing signal. A low score does not mean bullish or bearish.','#49432f')]:
        col.markdown(f'<div style="padding:20px;border-radius:19px;background:linear-gradient(135deg,{color},#162d34);border:1px solid #e5cd8055;box-shadow:0 5px 0 #081d25;min-height:160px"><strong style="font-size:19px;color:#f0dfaa">{title}</strong><p style="color:#dce7d6">{copy}</p></div>',unsafe_allow_html=True)
    st.markdown('**The idea:** an unusually call-heavy day while the index sells off is a bullish disagreement to investigate. Unusually put-heavy activity while the index rallies is the reverse. A high score measures disagreement, not the probability of a reversal.')
    with st.expander('What goes into the score?'):
        st.write('Whale lean = 2 × call-premium share − 1. Price move = same-session return / prior return standard deviation. Opposing pressure = max(0, −whale lean × price move). Index WARI = 100 × (1 − exp(−opposing pressure / 0.6)). Historical flow is not required.')
        st.write('0–24 little disagreement; 25–49 noticeable; 50–74 strong; 75–100 extreme. The scaling constant and labels are provisional. This is a new divergence extension, not a reproduction of the original six-component WARI or a fitted predictive model.')
        st.write('Example: 60% calls and a 3% index decline against 1% historical daily volatility produces 63/100, strong bullish disagreement. This illustrates the formula, not a current reading. Historical price baselines use earlier observations exclusively.')
        st.caption('Formula settings and calibration are maintained in code. The scale is read-only. Scores describe disagreement, not a tested reversal probability.')


def render_matched_snapshot(top):
    path=ROOT/'data/index_wari_snapshot.json'
    if not path.exists():
        return False
    try:
        saved=json.loads(path.read_text())
        sessions={r['date']:r for r in saved['sessions']}
        dates=sorted(sessions)
        if not dates:return False
        day=st.selectbox('SPY Magic session',dates,index=len(dates)-1,key='index_wari_matched_session')
        row=sessions[day]
        if row['baseline_end']>=day or row['price_as_of']>row['flow_as_of'] or row['baseline_sessions']<20:
            raise ValueError('Price and flow timing or prior baseline did not validate.')
        value,level,direction,_,pz=divergence(row['call_share'],.5,1,row['index_return'],row['return_std'])
        if direction=='No opposing signal':
            direction='Bearish agreement · puts and falling index' if row['call_share']<=.4 and row['index_return']<0 else 'Bullish agreement · calls and rising index' if row['call_share']>=.6 and row['index_return']>0 else 'Mixed / no opposing signal'
        detail=f"{day}: calls received {row['call_share']:.0%} of captured SPY Magic premium; SPY moved {row['index_return']:+.2%} from its prior close. Flow through {row['flow_as_of']} Pacific; matched underlying quote {row['price_as_of']}."
        if not row['complete_session'] or row['alerts']<20:
            level='PROVISIONAL · '+level
        with top.container():
            hero(value,level,detail,direction)
            if row['alerts']<20:
                st.warning(f"Only {row['alerts']} saved alerts in this partial session. This score is sensitive to each order; it is not a settled session signal.")
            a,b,c=st.columns(3)
            a.metric('📞 Call share of premium',f"{row['call_share']:.0%}")
            b.metric('SPY versus previous close',f"{row['index_return']:+.2%}")
            c.metric('Saved Magic alerts',str(row['alerts']))
        st.caption(f"Prior-price baseline: {row['baseline_sessions']} daily returns ending {row['baseline_end']}; daily volatility {row['return_std']:.2%}. Historical flow is not required. Intraday readings use daily volatility as a reference and are provisional.")
        st.caption('Uses captured alert-row aggregates, including repeated observations per contract. Premium labels are rounded; alerts are not necessarily unique trades or whales. Flow is compared with a neutral 50% reference, not an empirical broad-SPY flow baseline. Price volatility uses prior historical sessions.')
        if row.get('unknown_side_alerts'):
            st.caption(f"{row['unknown_side_alerts']} alerts have an unspecified displayed side. They remain in the user-supplied non-bid filter sample and are not relabeled ask-side.")
        st.dataframe([{'Session':r['date'],'Alerts':r['alerts'],'Call premium share':f"{r['call_share']:.1%}",
                       'SPY move':f"{r['index_return']:+.2%}",'Disagreement score':round(r['score'],1),
                       'Direction':r['direction'],'Coverage':'Saved completed-session capture' if r['complete_session'] else 'Partial session'}
                      for r in saved['sessions']],hide_index=True,use_container_width=True)
        with st.expander('Saved WARI inputs and sources'):
            st.link_button('SPY Magic alert filter',saved['flow_source_url'])
            st.link_button('SPY price source',saved['price_source_url'])
            st.write(row)
        return True
    except (OSError,ValueError,KeyError,TypeError) as exc:
        st.caption('Matched WARI snapshot unavailable: '+str(exc))
        return False


def render_saved_snapshot(top):
    if render_matched_snapshot(top):
        return
    path=ROOT/'data/prestige.json'
    if not path.exists():
        return
    try:
        saved=json.loads(path.read_text())
        rows=[]
        for card in saved.get('cards',[]):
            if card.get('last_side')!='ASK':
                continue
            amount=str(card.get('last_premium','')).replace('$','').replace(',','').strip()
            m=re.fullmatch(r'([0-9.]+)([KMB]?)',amount,re.I)
            if not m or card.get('type') not in ('call','put'):
                continue
            date=str(card.get('last',''))[:10]
            premium=float(m[1])*{'':1,'K':1000,'M':1000000,'B':1000000000}[m[2].upper()]
            rows.append((date,card['type'],premium))
        if not rows:
            return
        day=max(r[0] for r in rows)
        sample=[r for r in rows if r[0]==day]
        calls=sum(r[2] for r in sample if r[1]=='call')
        puts=sum(r[2] for r in sample if r[1]=='put')
        if calls+puts<=0:
            return
        share=calls/(calls+puts)
        direction='Bullish whale lean' if share>=.6 else 'Bearish whale lean' if share<=.4 else 'Mixed whale lean'
        color='#b9ef76' if share>=.6 else '#ff9b9b' if share<=.4 else '#efd58a'
        bg='#214b3a' if share>=.6 else '#572f38' if share<=.4 else '#49412d'
        with top.container():
            st.markdown(f'<div style="padding:27px;border-radius:24px;background:linear-gradient(125deg,{bg},#122e36);border:1px solid {color};box-shadow:0 6px 0 #071d24"><div style="color:#efd58a;font-weight:900;letter-spacing:.09em">INDEX WARI · SAVED WHALE SNAPSHOT</div><h2 style="color:{color}!important">{direction.upper()}</h2><div style="font-size:52px;font-weight:900;color:{color}">{share:.0%} calls</div><p style="color:#e1e8d6">The saved observations lean toward {"calls" if share>=.6 else "puts" if share<=.4 else "neither side clearly"}. This describes whale activity; price confirmation determines whether it is a divergence.</p><div style="height:19px;border-radius:12px;background:linear-gradient(90deg,#b44859 {100*(1-share):.1f}%,#83c867 {100*(1-share):.1f}%);"></div><p style="font-size:12px;color:#bdcfc4">Observed {html.escape(day)} Pacific · latest saved observation per contract · rounded premiums · not live or complete session totals</p></div>',unsafe_allow_html=True)
            st.caption('Divergence score: unavailable until matched index prices and SPY Magic session observations are connected. The call percentage above is a separate snapshot, not the divergence score.')
        a,b,c=st.columns(3)
        a.metric('📞 Calls in this snapshot',f'${calls:,.0f}')
        b.metric('🩸 Puts in this snapshot',f'${puts:,.0f}')
        c.metric('Saved contract observations',str(len(sample)))
    except (ValueError,KeyError,TypeError,OSError):
        return


def broad_gap(magic_call_share, broad_call_share):
    if not 0 <= magic_call_share <= 1 or not 0 <= broad_call_share <= 1:
        raise ValueError('Call shares must be between zero and one.')
    gap = 100 * (magic_call_share - broad_call_share)
    label = 'Bullish relative divergence' if gap >= 10 else 'Bearish relative divergence' if gap <= -10 else 'Similar to broad SPY flow'
    return gap, label

def render_broad_comparison(top):
    path=ROOT/'data/wari_comparison.json'
    st.markdown('### 🐋 Magic versus the rest of SPY')
    if not path.exists():
        st.markdown('**Broad SPY comparison: not yet captured.** This view will show whether Magic is more bullish or bearish than the broader SPY options activity over the same window.')
        st.caption('The saved contract lean above is not a broad-market comparison. Orange Swan’s filtered SPY alerts are not substituted for broad SPY flow.')
        return
    try:
        pair=json.loads(path.read_text())
        magic=pair['magic']
        broad=pair['broad']
        fields=['window_start','window_end','timezone','basis']
        if any(magic[k]!=broad[k] for k in fields):
            raise ValueError('Comparison windows and measurement basis must match.')
        if magic['basis'] not in ['premium','order_count','contract_volume']:
            raise ValueError('Unknown comparison basis.')
        if not magic.get('verified_on') or not broad.get('verified_on') or not magic.get('source_url') or not broad.get('source_url'):
            raise ValueError('Both observations need verified sources.')
        if not magic.get('complete_window') or not broad.get('complete_window'):
            raise ValueError('Both sources must cover the complete declared window.')
        mc=float(magic['calls']); mp=float(magic['puts'])
        bc=float(broad['calls']); bp=float(broad['puts'])
        if min(mc,mp,bc,bp)<0 or mc+mp<=0 or bc+bp<=0:
            raise ValueError('Invalid call/put totals.')
        m=mc/(mc+mp); p=bc/(bc+bp)
        gap,label=broad_gap(m,p)
        direction='Bullish relative whale lean' if gap>=10 else 'Bearish relative whale lean' if gap<=-10 else 'Mixed / similar whale lean'
        detail=f'Magic is {m:.0%} calls versus {p:.0%} for broad SPY flow, a {gap:+.1f} percentage-point gap. Window: {magic["window_start"]} to {magic["window_end"]} {magic["timezone"]}. Basis: {magic["basis"]}.'
        with top.container():
            hero(abs(gap),label,detail,direction)
            st.caption('Score = absolute percentage-point gap, 0–100. Direction shows whether Magic is relatively more bullish or bearish. This is separate from the price-divergence score.')
        a,b,c=st.columns(3)
        a.metric('Magic calls',f'{m:.0%}')
        b.metric('Broad SPY calls',f'{p:.0%}')
        c.metric('Magic minus broad SPY',f'{gap:+.1f} points')
        st.caption('Relative bullishness can still occur with a put-heavy Magic sample. Compare the absolute call shares too. The 10-point descriptor cutoff is provisional.')
        with st.expander('Comparison sources'):
            st.link_button('SPY Magic source',magic['source_url'])
            st.link_button('Broad SPY source',broad['source_url'])
    except (ValueError,KeyError,TypeError,OSError) as exc:
        st.caption('Broad SPY comparison unavailable: '+str(exc))

