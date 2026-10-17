"""WARI research dashboard: observed flow, never synthetic positioning."""
from pathlib import Path
import json
import re
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
ORANGE_URL = 'https://unusualwhales.com/option-flow-alerts?is_bid_side=false&is_multi_leg=false&is_otm=true&limit=250&min_ask_perc=0.7&min_dte=2&min_premium=10000&ticker_symbol=SMH%2CBABA%2CJD%2CSPY%2CQQQ&vol_greater_oi=true&watchlist_name=Orange%20Swan%20BETA'


def prepare(raw):
    aliases = {'ticker_symbol':'ticker','symbol':'ticker','call or put':'type','option_type':'type','trade date':'date','time':'date','premium':'premium'}
    df = raw.rename(columns={c: aliases.get(str(c).strip().lower(), str(c).strip().lower()) for c in raw.columns}).copy()
    if df.columns.duplicated().any():
        raise ValueError('Multiple columns map to the same field. Keep one ticker, type, date and premium column.')
    needed = {'ticker','type','date','premium'}
    if not needed.issubset(df.columns):
        raise ValueError('Required columns: ticker, type (call/put), date, premium. UW Symbol, Call or Put and Time names also work.')
    dates = df['date'].astype(str)
    parsed = pd.to_datetime(dates, errors='coerce', utc=True).dt.tz_convert('America/New_York').dt.date.copy()
    date_only = dates.str.fullmatch(r'\d{4}-\d{2}-\d{2}')
    parsed.loc[date_only] = pd.to_datetime(dates.loc[date_only], errors='coerce').dt.date
    df['date'] = parsed
    df['ticker'] = df['ticker'].astype(str).str.upper().str.strip().str.lstrip('$')
    df['type'] = df['type'].astype(str).str.lower().str.strip().replace({'c':'call','p':'put','calls':'call','puts':'put'})
    df['premium'] = pd.to_numeric(df['premium'].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce')
    valid = df['date'].notna() & df['type'].isin(['call','put']) & df['premium'].gt(0) & df['ticker'].ne('')
    rejected = int((~valid).sum())
    df = df.loc[valid].copy()
    # Keep separate genuine prints; only explicit IDs permit reliable deduplication.
    for key in ['id','trade_id','alert_id']:
        if key in df.columns:
            present = df[key].notna() & df[key].astype(str).ne('')
            df = pd.concat([df.loc[present].drop_duplicates(key), df.loc[~present]])
            break
    return df, rejected


def score(df):
    if df.empty:
        return None
    calls = df['type'].eq('call')
    dollar_share = df.loc[calls, 'premium'].sum() / df['premium'].sum()
    print_share = calls.mean()
    value = 100 * (0.7 * dollar_share + 0.3 * print_share)
    return {'score': float(value), 'prints': len(df), 'premium': float(df['premium'].sum()), 'call_dollars': float(dollar_share * 100), 'call_prints': float(print_share * 100)}


def gauge(value):
    marker = '' if value is None else f'<span style="position:absolute;left:{max(1,min(99,value))}%;top:-8px;color:#fff;font-size:25px;text-shadow:0 2px 4px #000">▼</span>'
    st.markdown(f'<div style="position:relative;height:24px;border-radius:14px;background:linear-gradient(90deg,#a73a48,#e4b966,#8ac95d);margin:22px 8px 8px">{marker}</div><div style="display:flex;justify-content:space-between;color:#d9dfc2;font-weight:800"><span>🩸 Put-heavy</span><span>Mixed bag</span><span>Call-heavy 📞</span></div>', unsafe_allow_html=True)


def render(mode='wari'):
    if mode == 'orange':
        st.markdown('<h1 class="rambo-title">Orange Swan 🍊</h1><div class="subhead">Who’s breaking from the pack?</div>', unsafe_allow_html=True)
    else:
        st.markdown('<h1 class="rambo-title">WARI 🐋</h1><div class="subhead">Whale Alert Risk Indicator</div>', unsafe_allow_html=True)
        st.write('Powered by SPY Magic. Watch where the whale activity leans, then check whether SPY price agrees.')
    upload = None
    orange_upload = None
    def load_sample(uploaded, filename, tickers):
        source = ROOT / 'data' / filename
        if uploaded is None and not source.exists():
            return pd.DataFrame()
        try:
            sample, rejected = prepare(pd.read_csv(uploaded if uploaded is not None else source))
            if rejected:
                st.caption(f'{filename}: {rejected} invalid rows excluded.')
            return sample.loc[sample['ticker'].isin(tickers)].copy()
        except (ValueError, TypeError) as exc:
            st.error(str(exc))
            return pd.DataFrame()
    df = load_sample(upload, 'spy_magic_flow.csv', ['SPY'])
    orange_df = load_sample(orange_upload, 'orange_swan_flow.csv', ['SPY','QQQ','SMH','BABA','JD'])
    snapshot_mode = False
    if mode == 'orange':
        render_orange(orange_df)
        return
    if df.empty:
        saved = ROOT / 'data/prestige.json'
        if saved.exists():
            try:
                snapshot = json.loads(saved.read_text())
                rows = []
                for card in snapshot.get('cards', []):
                    premium = str(card.get('last_premium', '')).replace('$','').replace(',','').strip()
                    found = re.fullmatch(r'([0-9.]+)([KMB]?)', premium, re.I)
                    if not found:
                        continue
                    amount = float(found[1]) * {'':1,'K':1000,'M':1000000,'B':1000000000}[found[2].upper()]
                    if card.get('last_side') != 'ASK':
                        continue
                    rows.append({'ticker':'SPY', 'type':card.get('type'), 'date':str(card.get('last',''))[:10].replace('/','-'), 'premium':amount})
                if rows:
                    df, _ = prepare(pd.DataFrame(rows))
                    snapshot_mode = True
                    st.caption('Saved SPY Magic contract snapshot · last alert: '+str(snapshot.get('latest_alert_time', snapshot.get('source_time','unknown')))+' Pacific')
                    st.info('Showing the last saved ask-side observation per contract. Dollar values are rounded display amounts. This is a contract snapshot, not the complete session flow or a live WARI reading.')
            except (ValueError, TypeError, KeyError):
                st.caption('Saved SPY Magic snapshot could not be read.')
    if not df.empty:
        dates = sorted(df['date'].unique())
        chosen = st.selectbox('SPY Magic session', dates, index=len(dates)-1, key='wari_session')
        today = df.loc[df['date'].eq(chosen)]
        st.caption(f'SPY Magic · {chosen} · {len(today):,} observations · filtered SPY activity')
    else:
        today = df
    with st.container():
        reading = score(today)
        st.markdown('### What are the whales leaning toward?')
        gauge(None if reading is None else reading['score'])
        if reading:
            n = reading['score']
            label = 'Call-heavy' if n >= 60 else 'Put-heavy' if n <= 40 else 'Mixed / no clear lean'
            st.metric('Saved contract lean' if snapshot_mode else 'WARI direction · research beta', f'{n:.0f} / 100', label, delta_color='off')
            cols = st.columns(3)
            cols[0].metric('Call share of dollars', f"{reading['call_dollars']:.0f}%")
            cols[1].metric('Call share of prints', f"{reading['call_prints']:.0f}%")
            cols[2].metric('Observed premium', f"${reading['premium']:,.0f}")
            if reading['prints'] < 20: st.info('Thin sample: fewer than 20 prints. A few orders can swing this reading.')
            rows = []
            for day, group in df.groupby('date'):
                rows.append({'Session':day,'Whale direction':score(group)['score']})
            if not snapshot_mode:
                st.line_chart(pd.DataFrame(rows).set_index('Session'), y='Whale direction', color='#b8ee69')
        else:
            st.markdown('### Waiting for the SPY Magic snapshot')
            st.write('The latest SPY Magic observation is unavailable in this session.')
        st.markdown('**🤝 Agreement:** calls and rising prices, or puts and falling prices. **👀 Plot twist:** call-heavy activity while price falls, or put-heavy activity while price rises. Neither guarantees the next move.')
        prices_path = ROOT / 'data/wari_prices.csv'
        if not today.empty and prices_path.exists():
            try:
                prices = pd.read_csv(prices_path)
                prices['date'] = pd.to_datetime(prices['date']).dt.date
                prices['ticker'] = prices['ticker'].str.upper()
                prices['close'] = pd.to_numeric(prices['close'], errors='raise')
                prices = prices.sort_values(['ticker','date']).drop_duplicates(['ticker','date'],keep='last')
                prices['return'] = prices.groupby('ticker')['close'].pct_change(fill_method=None)
                records=[]
                for ticker, group in today.groupby('ticker'):
                    px=prices.loc[prices['ticker'].eq(ticker)&prices['date'].eq(chosen)]
                    if px.empty or pd.isna(px.iloc[-1]['return']): continue
                    s=score(group)['score']; r=float(px.iloc[-1]['return'])
                    contrary=(s>=60 and r<0) or (s<=40 and r>0)
                    records.append({'Ticker':'$'+ticker,'Whale direction':round(s,1),'Price change':f'{r:+.2%}','Read':'👀 Opposite directions' if contrary else 'Mixed' if 40<s<60 or r==0 else '🤝 Same direction'})
                if records: st.dataframe(records,hide_index=True,width='stretch')
            except (ValueError, KeyError, TypeError): st.caption('Price comparison unavailable: reference data could not be validated.')
    with st.expander('How we read it'):
        st.markdown('### A number you can actually unpack')
        st.write('WARI reads only the SPY Magic sample. Orange Swan is calculated separately from its own filter. WARI direction = 70% × call share of premium + 30% × call share of prints, expressed on a 0–100 scale. 50 means balanced; 60+ is call-heavy; 40 or less is put-heavy. These are provisional descriptive cutoffs, not fitted trading thresholds.')
        st.write('Premium tells us where dollars are leaning. Print share checks whether that lean appears across orders. Large and near-term orders belong in the supporting evidence, not automatic bullish bonuses. Calls can hedge shorts; puts can hedge longs. Multiple prints can come from one participant.')
        st.markdown('**What would earn the word predictive?** Freeze the filter and test daily signals against subsequent 1-, 3- and 5-session returns. Compare direction-only, equal-weight and premium-heavy versions on training periods, choose using chronological validation, then evaluate once on a later untouched period. Purge overlapping forward-return windows between splits. Report sample size, balanced accuracy, false alarms and returns after costs against simple market baselines.')
        st.write('For contrarian tests, define the price/flow disagreement before the outcome, then measure later reversals separately from ordinary trend-following signals. Never use prices or orders arriving after the signal timestamp to construct it.')
        st.info('The attached notes supply formulas and claimed yearly results, but not the referenced 2023–2025 trade files or aligned market prices. Predictive ranking is therefore untested. This beta does not reproduce forced 1.05/0.47 historical scores or label reduced filtered activity as a liquidity exit.')


def render_orange(orange_df):
    if orange_df.empty and render_orange_saved():
        return
    if not orange_df.empty:
        orange_dates = sorted(orange_df['date'].unique())
        orange_day = st.selectbox('Orange Swan session', orange_dates, index=len(orange_dates)-1, key='orange_session')
        today = orange_df.loc[orange_df['date'].eq(orange_day)]
        st.caption(f'Orange Swan snapshot · {orange_day} · {len(today):,} prints')
    else:
        today = orange_df
        st.caption('Waiting for an Orange Swan snapshot.')
    st.markdown('### 🍊 Orange Swan · who is breaking from the pack?')
    st.write('SPY and QQQ set the broad-market reference. SMH represents semis; BABA and JD are two China-linked names, not the entire Chinese market. We watch for their flow to pull apart.')
    st.link_button('Open the Orange Swan filter ↗', ORANGE_URL)
    st.caption('Filter: ask share ≥70% · premium ≥$10,000 · ≥2 DTE · OTM · single-leg · volume above open interest. The linked view caps results at 250; it is not a complete historical dataset.')
    broad = today.loc[today['ticker'].isin(['SPY','QQQ'])] if not today.empty else today
    base = score(broad)
    cards=st.columns(3)
    for col,(name,tickers) in zip(cards,[('🌎 Broad market',['SPY','QQQ']),('🔌 Semis',['SMH']),('🐉 China names',['BABA','JD'])]):
        subset=today.loc[today['ticker'].isin(tickers)] if not today.empty else today
        s=score(subset)
        with col.container(border=True):
            st.markdown('**'+name+'**')
            st.caption(' / '.join('$'+t for t in tickers))
            st.metric('Whale direction', '—' if s is None else f"{s['score']:.0f} / 100")
            if s and base and name!='🌎 Broad market':
                gap=s['score']-base['score']
                st.caption(f'{gap:+.0f} points versus broad flow · '+('meaningful split to investigate' if abs(gap)>=20 else 'no large split'))
            if s: st.caption(f"{s['prints']} prints · ${s['premium']:,.0f}")
    st.write('A flow split flags a research lead. To call it price decoupling, compare same-session returns with SPY/QQQ too. It does not identify the cause or predict a tariff announcement.')
    st.markdown('**From Milt’s research notebook:** Milt reports that the original Orange Swan alarm helped identify 40-bagger opportunities ahead of the 2025 tariff trade wars. The dated alerts and entry/exit prices have not yet been audited in this Terminal; this is reported history, not a tested hit rate.')


def render_orange_saved():
    path = ROOT / 'data/orange_swan_summary.json'
    if not path.exists():
        return False
    try:
        saved = json.loads(path.read_text())
        all_rows = pd.DataFrame(saved['summary'])
        day = all_rows['date'].max()
        rows = all_rows.loc[all_rows['date'].eq(day)]
    except (ValueError, KeyError, OSError):
        return False
    st.caption(f'Delayed Orange Swan capture · latest displayed date {day} · captured {saved["captured_on"]}')
    st.write('Where is the whale activity pulling apart? Compare the broad-market sample with semis and China-linked names.')
    def grouped(symbols):
        sample = rows.loc[rows.ticker.isin(symbols)]
        if sample.empty:
            return None
        p = sample.premium.sum()
        n = sample.prints.sum()
        return 100*(.7*sample.call_premium.sum()/p + .3*sample.call_prints.sum()/n), int(n), p
    broad = grouped(['SPY','QQQ'])
    groups = [('🌎 Broad market',['SPY','QQQ']),('🔌 Semis',['SMH']),('🐉 China names',['BABA','JD'])]
    for col,(title,symbols) in zip(st.columns(3),groups):
        with col.container(border=True):
            st.markdown('**'+title+'**')
            st.markdown('<div style="height:7px;border-radius:8px;background:linear-gradient(90deg,#9be46b,#d9bd6c,#d9646a);margin-bottom:16px"></div>',unsafe_allow_html=True)
            reading = grouped(symbols)
            if reading:
                value,n,premium = reading
                st.metric('Whale direction',f'{value:.0f} / 100')
                st.caption(f'{n} alerts · ${premium:,.0f} observed premium')
                st.markdown('**📞 BULLISH lean**' if value>=60 else '**🩸 BEARISH lean**' if value<=40 else '**🔀 MIXED**')
                if broad and title!='🌎 Broad market':
                    st.caption(f'{value-broad[0]:+.0f} points versus broad-market flow')
            else:
                st.metric('Whale direction','—')
            missing=[t for t in symbols if t not in rows.ticker.values]
            if missing:
                st.caption('No observations for '+', '.join('$'+t for t in missing)+' in this date’s captured sample.')
    st.caption('0 = put-heavy · 50 = balanced · 100 = call-heavy. This measures observed flow direction, not the probability of a trade succeeding.')
    st.info(saved['coverage'])
    with st.expander('Captured observations by ticker and date'):
        st.dataframe(all_rows,hide_index=True,width='stretch')
    st.link_button('Open Orange Swan filter ↗',ORANGE_URL)
    st.markdown('**From Milt’s research notebook:** Milt reports that the original Orange Swan alarm helped identify 40-bagger opportunities ahead of the 2025 tariff trade wars. Dated alerts and entry/exit prices have not yet been audited in this Terminal.')
    return True
