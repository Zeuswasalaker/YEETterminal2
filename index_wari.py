"""Index WARI: baseline-relative disagreement between flow and price."""
from pathlib import Path
from math import exp
import html
import pandas as pd
import streamlit as st
from wari import prepare

ROOT = Path(__file__).parent

def divergence(call_share, baseline_share, share_std, index_return, return_std):
    if share_std <= 0 or return_std <= 0:
        raise ValueError('Historical dispersion must be positive.')
    flow_z = (call_share - baseline_share) / share_std
    price_z = index_return / return_std
    conflict = max(0.0, -flow_z * price_z)
    value = 100 * (1 - exp(-conflict / 3))
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

def historical_scores(flow, prices, window=60, minimum=20):
    close=pd.to_numeric(prices, errors='coerce').dropna().sort_index()
    close.index=pd.to_datetime(close.index).tz_localize(None).normalize()
    close=close[~close.index.duplicated(keep='last')]
    returns=close.pct_change(fill_method=None)
    out=flow.join(returns.rename('return'),how='left')
    # All baselines end before the signal date. Missing sessions are not zero flow.
    out['flow_mean']=flow.call_share.shift(1).rolling(window,min_periods=minimum).mean()
    out['flow_std']=flow.call_share.shift(1).rolling(window,min_periods=minimum).std()
    out['price_std']=returns.shift(1).rolling(window,min_periods=minimum).std().reindex(out.index)
    for day,row in out.iterrows():
        fields=['call_share','flow_mean','flow_std','return','price_std']
        if row[fields].notna().all() and row.flow_std>0 and row.price_std>0:
            result=divergence(row.call_share,row.flow_mean,row.flow_std,row['return'],row.price_std)
            out.loc[day,'Index WARI']=result[0]
    return out

def hero(value=None, level='Historical comparison pending', detail='A baseline-relative reading needs matched historical SPY Magic sessions and index prices.', direction=''):
    number='—' if value is None else f'{value:.0f}<span style="font-size:22px"> / 100</span>'
    st.markdown(f'<div style="padding:26px;border-radius:24px;background:linear-gradient(120deg,#214b3a,#122e36);border:1px solid #b9ef7666;box-shadow:0 6px 0 #071d24;margin-bottom:24px"><div style="color:#b9ef76;font-weight:900;letter-spacing:.12em">INDEX WARI · WHALE / PRICE DIVERGENCE</div><div style="font-size:64px;font-weight:900;color:#efd58a;line-height:1.2">{number}</div><div style="font-size:25px;font-weight:800;color:#b9ef76">{html.escape(level)}</div><p style="font-size:17px;color:#e2ebd4">{html.escape(direction)}</p><p style="color:#c0d3c8">{html.escape(detail)}</p></div>',unsafe_allow_html=True)

def render():
    st.markdown('<h1 class="rambo-title">Index WARI 🐋</h1>',unsafe_allow_html=True)
    top=st.empty()
    with top.container(): hero()
    flow_path=ROOT/'data/spy_magic_flow.csv'
    price_path=ROOT/'data/wari_prices.csv'
    raw=None
    if flow_path.exists():
        try: raw=pd.read_csv(flow_path)
        except (ValueError,OSError): pass
    with st.expander('milt stuff'):
        st.caption('Use dated SPY Magic alerts from a consistent filter. Full sessions only: do not mix incomplete intraday samples with full-day baselines. Inputs remain in this session.')
        uploaded=st.file_uploader('SPY Magic historical alerts',type=['csv'],key='index_wari_flow')
        price_upload=st.file_uploader('Historical SPY prices · Date, Close',type=['csv'],key='index_wari_price')
        complete=st.checkbox('These flow dates represent comparable complete sessions',value=False,key='index_wari_complete')
    if uploaded:
        try: raw=pd.read_csv(uploaded)
        except ValueError as exc: st.error(str(exc))
    prices=None
    if price_upload or price_path.exists():
        try:
            p=pd.read_csv(price_upload if price_upload else price_path)
            p.columns=[str(c).lower().strip() for c in p.columns]
            if 'ticker' in p: p=p.loc[p.ticker.str.upper().eq('SPY')]
            prices=pd.Series(pd.to_numeric(p['close']).values,index=pd.to_datetime(p['date']))
        except (ValueError,KeyError): st.caption('Price reference could not be validated.')
    if raw is not None:
        try:
            flow=daily_flow(raw)
            if not flow.empty and prices is not None and complete:
                results=historical_scores(flow,prices)
                usable=results.dropna(subset=['Index WARI']) if 'Index WARI' in results else pd.DataFrame()
                if not usable.empty:
                    day=st.selectbox('Completed session',list(usable.index),index=len(usable)-1)
                    row=usable.loc[day]
                    v,level,direction,fz,pz=divergence(row.call_share,row.flow_mean,row.flow_std,row['return'],row.price_std)
                    detail=f'{day.date()}: calls received {row.call_share:.0%} of observed premium versus a {row.flow_mean:.0%} prior average. SPY moved {row["return"]:+.2%}, or {pz:+.1f} times its historical daily volatility. Flow is {fz:+.1f} standard deviations from its own prior baseline.'
                    with top.container(): hero(v,level,detail,direction)
                    st.line_chart(usable[['Index WARI']],color='#b9ef76')
                    st.caption('Prior 60 observations, minimum 20. Incomplete and missing sessions must be resolved before relying on this history.')
                else: st.info('At least 20 prior flow sessions and price returns with nonzero variation are needed.')
        except (ValueError,KeyError,TypeError) as exc: st.error(str(exc))
    st.markdown('**The idea:** an unusually call-heavy day while the index sells off is a bullish disagreement to investigate. Unusually put-heavy activity while the index rallies is the reverse. A high score measures disagreement, not the probability of a reversal.')
    with st.expander('Try the 60% calls + big down day example',expanded=True):
        st.caption('ILLUSTRATIVE SCENARIO · these controls are assumptions, not a current market reading.')
        a,b=st.columns(2)
        calls=a.slider('Call share of premium (%)',0,100,60,key='iw_calls')/100
        move=b.slider('Index daily move (%)',-6.0,6.0,-3.0,0.1,key='iw_move')/100
        c,d,e=st.columns(3)
        base=c.number_input('Historical average call share (%)',0.0,100.0,50.0,key='iw_base')/100
        fs=d.number_input('Typical call-share variation (percentage points)',0.1,50.0,10.0,key='iw_fs')/100
        ps=e.number_input('Typical daily index volatility (%)',0.1,10.0,1.0,key='iw_ps')/100
        v,label,direction,fz,pz=divergence(calls,base,fs,move,ps)
        st.metric('Scenario divergence',f'{v:.0f} / 100',label,delta_color='off')
        st.write(f'{direction}. Whale lean is {fz:+.1f} standard deviations from the assumed baseline; price is {pz:+.1f} daily-volatility units from flat.')
    with st.expander('What goes into the score?'):
        st.write('Flow surprise = (call-premium share − prior mean) / prior standard deviation. Price move = same-session return / prior return standard deviation. Opposing pressure = max(0, −flow surprise × price move). Index WARI = 100 × (1 − exp(−opposing pressure / 3)).')
        st.write('0–24 little disagreement; 25–49 noticeable; 50–74 strong; 75–100 extreme. The scaling constant and labels are provisional. This is a new divergence extension, not a reproduction of the original six-component WARI or a fitted predictive model.')
        st.write('A 60% call share can be ordinary if history also averages 60%. It only becomes unusual relative to its own baseline. Baselines use earlier observations exclusively. Calls and puts may hedge other positions; flow does not reveal the entire book.')
        st.caption('The existing contract cards are not a historical session dataset. The attached methodology references historical workbooks that are not present in the current repository or uploads. No historical result is manufactured from those cards.')
