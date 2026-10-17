"""Index WARI: baseline-relative disagreement between flow and price."""
from pathlib import Path
from math import exp
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
    number='—' if value is None else f'{value:.0f}<span style="font-size:22px"> / 100</span>'
    position = 0 if value is None else max(0, min(100, value))
    pointer = '' if value is None else f'<span style="position:absolute;left:{position}%;top:-12px;transform:translateX(-50%);font-size:26px;color:#fff">▼</span>'
    scale = f'<div role="img" aria-label="Divergence scale, {value if value is not None else "unavailable"} out of 100" style="position:relative;height:20px;border-radius:12px;background:linear-gradient(90deg,#398a73,#e8c66c,#e17c49,#b84062);margin:22px 12px 8px">{pointer}</div><div style="display:flex;justify-content:space-between;font-size:12px;color:#d5dfcb"><span>0 · little</span><span>50 · strong</span><span>100 · extreme</span></div>'
    st.markdown(f'<div style="padding:26px;border-radius:24px;background:linear-gradient(120deg,#214b3a,#122e36);border:1px solid #b9ef7666;box-shadow:0 6px 0 #071d24;margin-bottom:24px"><div style="color:#b9ef76;font-weight:900;letter-spacing:.12em">INDEX WARI · WHALE / PRICE DIVERGENCE</div><div style="font-size:64px;font-weight:900;color:#efd58a;line-height:1.2">{number}</div><div style="font-size:25px;font-weight:800;color:#b9ef76">{html.escape(level)}</div><p style="font-size:17px;color:#e2ebd4">{html.escape(direction)}</p><p style="color:#c0d3c8">{html.escape(detail)}</p>{scale}</div>',unsafe_allow_html=True)

def render():
    top=st.empty()
    with top.container(): hero()
    st.caption('Whale Alert Risk Indicator · SPY Magic versus SPY price')
    flow_path=ROOT/'data/spy_magic_flow.csv'
    price_path=ROOT/'data/wari_prices.csv'
    raw=None
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
                    st.line_chart(usable[['Index WARI']],color='#b9ef76')
                    st.caption('Price baseline: prior 60 index returns, minimum 20. Flow and price must cover the same completed session.')
                else: st.info('A matched flow session and at least 20 prior index returns with nonzero volatility are needed.')
        except (ValueError,KeyError,TypeError) as exc: st.error(str(exc))
    st.markdown('**The idea:** an unusually call-heavy day while the index sells off is a bullish disagreement to investigate. Unusually put-heavy activity while the index rallies is the reverse. A high score measures disagreement, not the probability of a reversal.')
    with st.expander('What goes into the score?'):
        st.write('Whale lean = 2 × call-premium share − 1. Price move = same-session return / prior return standard deviation. Opposing pressure = max(0, −whale lean × price move). Index WARI = 100 × (1 − exp(−opposing pressure / 0.6)). Historical flow is not required.')
        st.write('0–24 little disagreement; 25–49 noticeable; 50–74 strong; 75–100 extreme. The scaling constant and labels are provisional. This is a new divergence extension, not a reproduction of the original six-component WARI or a fitted predictive model.')
        st.write('Example: 60% calls and a 3% index decline against 1% historical daily volatility produces 63/100, strong bullish disagreement. This illustrates the formula, not a current reading. Historical price baselines use earlier observations exclusively.')
        st.caption('Formula settings and calibration are maintained in code. The scale is read-only. Scores describe disagreement, not a tested reversal probability.')
