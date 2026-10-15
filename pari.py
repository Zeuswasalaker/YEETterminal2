"""Original PARI, calculated from actual close prices only."""
import pandas as pd

FRAMES = {'5 minute': '5min', '10 minute': '10min', '1 hour': '60min', '4 hour': '240min', 'Daily': None}

def calculate(close):
    close = pd.to_numeric(close, errors='coerce').dropna().sort_index()
    close = close[~close.index.duplicated(keep='last')]
    if (close <= 0).any():
        raise ValueError('Close prices must be positive.')
    df = close.rename('Close').to_frame()
    df['Return'] = close.pct_change(fill_method=None)
    df['Volatility'] = df.Return.rolling(10).std()
    df['Momentum'] = close - close.shift(10)
    df['Trend_Persistence'] = df.Return.rolling(10).mean()
    df['PARI'] = 50 + 50 * df.Momentum.rank(pct=True) - 50 * df.Volatility.rank(pct=True)
    return df

def read_csv(file):
    df = pd.read_csv(file)
    columns = {str(c).strip().lower(): c for c in df.columns}
    date = next((columns[c] for c in ('datetime', 'timestamp', 'date') if c in columns), None)
    if date is None or 'close' not in columns:
        raise ValueError('CSV needs Date (or Datetime/Timestamp) and Close columns.')
    dates = pd.to_datetime(df[date], errors='raise')
    return pd.Series(pd.to_numeric(df[columns['close']], errors='raise').values, index=pd.DatetimeIndex(dates), name='Close')

def aggregate(close, rule):
    """Anchor each regular session at 09:30 NY; retain complete fixed-duration bars."""
    if close.index.tz is None:
        raise ValueError('Automatic aggregation requires timezone-aware timestamps.')
    close = close.tz_convert('America/New_York').sort_index().between_time('09:30', '15:59')
    pieces = []
    expected = int(pd.Timedelta(rule) / pd.Timedelta('5min'))
    now = pd.Timestamp.now(tz='America/New_York')
    for _, day in close.groupby(close.index.date):
        bars = day.resample(rule, origin='start_day', offset='9h30min').agg(['last', 'count'])
        bars = bars[(bars['count'] == expected) & (bars.index + pd.Timedelta(rule) <= now)]
        pieces.append(bars['last'])
    return pd.concat(pieces).rename('Close') if pieces else pd.Series(dtype=float, name='Close')

def yahoo(frame):
    import yfinance as yf
    if frame == 'Daily':
        data = yf.Ticker('SPY').history(period='5y', interval='1d', auto_adjust=False, prepost=False, raise_errors=True)
        close = data['Close']
        # Conservatively exclude today's daily candle until the regular close.
        now = pd.Timestamp.now(tz='America/New_York')
        if now.hour < 16:
            close = close[close.index.date < now.date()]
        return close
    data = yf.Ticker('SPY').history(period='1mo', interval='5m', auto_adjust=False, prepost=False, raise_errors=True)
    return aggregate(data['Close'], FRAMES[frame])

def posture(valid):
    latest = valid.iloc[-1]
    bars = min(5, len(valid)-1)
    change = float(latest.PARI-valid.iloc[-1-bars].PARI) if bars else 0.0
    direction = 'RISING' if change > 2 else 'FALLING' if change < -2 else 'FLAT'
    if not bars:
        return 'WAIT FOR MORE DATA', 'One reading is not enough to establish a direction.', '#94a9b5', 'UNAVAILABLE', change, bars
    if latest.PARI > 50 and latest.Momentum > 0 and direction == 'RISING':
        return 'LEAN BULLISH', 'Look for bullish confirmation. PARI is improving and price momentum is positive.', '#a5ed3c', direction, change, bars
    if latest.PARI < 50 and latest.Momentum < 0 and direction == 'FALLING':
        return 'STAY DEFENSIVE', 'Favor caution with new longs. PARI is weakening alongside negative price momentum.', '#f4ac84', direction, change, bars
    if direction == 'FLAT':
        return 'BE PATIENT', 'PARI is holding steady. Wait for a clearer shift before treating this as directional confirmation.', '#21c9ab', direction, change, bars
    return 'WAIT FOR CONFIRMATION', 'The score and price momentum are mixed. Let price confirm the direction before acting on this reading.', '#e7cf83', direction, change, bars


def trend_chart(valid, count):
    import altair as alt
    recent = valid.tail(count).copy()
    plot = pd.DataFrame({'Bar': range(len(recent)), 'PARI': recent.PARI.values,
                         'Timestamp': [str(x) for x in recent.index]})
    change = plot.PARI.iloc[-1] - plot.PARI.iloc[0]
    color = '#a5ed3c' if change > 2 else '#f4ac84' if change < -2 else '#21c9ab'
    base = alt.Chart(plot).encode(
        x=alt.X('Bar:Q', axis=alt.Axis(title=None, labels=False, ticks=False, grid=False)),
        y=alt.Y('PARI:Q', scale=alt.Scale(domain=[0,100]), axis=alt.Axis(title=None, values=[0,25,50,75,100], gridColor='#24434d', labelColor='#8ca5ae')),
        tooltip=[alt.Tooltip('Timestamp:N', title='Bar start'), alt.Tooltip('PARI:Q', format='.2f')])
    reference = alt.Chart(pd.DataFrame({'Level':[50]})).mark_rule(color='#69818a', strokeDash=[4,6], opacity=.5).encode(y='Level:Q')
    line = base.mark_line(color=color, strokeWidth=2.5)
    point = base.transform_filter(alt.datum.Bar == len(plot)-1).mark_point(color=color, filled=True, size=75)
    return (reference+line+point).properties(height=240).configure_view(stroke=None).configure(background='#112b37')


def render(admin=None):
    import streamlit as st
    st.title('PARI')
    st.markdown('''<style>
.pari-kicker{font:700 11px Arial,sans-serif;letter-spacing:.18em;color:#20cba6;text-transform:uppercase;margin-bottom:9px}
.pari-snapshot{padding:25px 30px;border-radius:20px;background:linear-gradient(120deg,#1c4148,#102d38);border:1px solid #32c6a544;box-shadow:0 14px 35px #0003;margin:8px 0 24px}
.pari-action{font:800 clamp(24px,4vw,38px) Arial,sans-serif;letter-spacing:-.035em;margin-bottom:9px}
.pari-copy{color:#aac3c9;font-size:16px;line-height:1.6;max-width:850px}
.pari-stats{color:#67d9be;font-size:14px;margin-top:15px;font-weight:600}
[data-testid="stMetricValue"]{color:#a5ed3c;font-family:Arial,sans-serif;font-weight:800}
[data-testid="stMetricLabel"]{color:#81b6bc}
</style>''', unsafe_allow_html=True)
    st.markdown('<div class="pari-kicker">SPY / PRICE ACTION / FIVE TIMEFRAMES</div>', unsafe_allow_html=True)
    snapshot = st.empty()
    snapshot.markdown('<div class="pari-snapshot"><div class="pari-kicker">CURRENT POSTURE</div><div class="pari-action" style="color:#21c9ab">NO READING AVAILABLE</div><div class="pari-copy">Choose a timeframe to see the latest available reading.</div></div>', unsafe_allow_html=True)
    frame = st.radio('Timeframe', list(FRAMES), horizontal=True)
    source='Yahoo SPY'
    upload=None
    with st.container(key='milt_pari'), st.expander('milt stuff'):
        if admin and admin():
            source=st.radio('Price source',['Yahoo SPY','Upload price CSV'],horizontal=True)
            st.caption('Daily: five years. Intraday: one month of five-minute bars. CSVs must already match the selected timeframe and contain completed candles.')
            if source=='Upload price CSV':
                upload=st.file_uploader('SPY price history',type=['csv'],key='pari_csv_'+frame)
    close=None
    if source=='Upload price CSV':
        if upload:
            try:
                close=read_csv(upload)
                if frame!='Daily' and (close.index==close.index.normalize()).all():
                    raise ValueError('Intraday readings require intraday candles.')
            except Exception as exc:
                st.error(str(exc))
    else:
        @st.cache_data(ttl=300,show_spinner=False)
        def load(selected):
            return yahoo(selected)
        if st.button('↻ Refresh',type='primary'):
            load.clear()
        try:
            with st.spinner('Checking SPY…'):
                close=load(frame)
        except Exception:
            st.caption('SPY prices are temporarily unavailable. No current reading is shown.')
    if close is not None:
        try:
            df = calculate(close)
            valid = df.dropna(subset=['PARI'])
            if valid.empty:
                st.caption('Not enough price history for a reading yet.')
            else:
                from html import escape
                current = valid.iloc[-1]
                action, explanation, accent, direction, change, bars = posture(valid)
                timestamp = escape(str(valid.index[-1]))
                snapshot.markdown(f'<div class="pari-snapshot"><div class="pari-kicker">CURRENT POSTURE / {escape(frame)} / SPY</div><div class="pari-action" style="color:{accent}">{action}</div><div class="pari-copy">{explanation}</div><div class="pari-stats">PARI {current.PARI:.2f} · {direction} · {change:+.2f} points over {bars} bars</div><div class="pari-copy" style="font-size:12px;margin-top:10px">As of bar start {timestamp}. Summary of this timeframe only. A descriptive guide, not a tested trading signal.</div></div>', unsafe_allow_html=True)
                a, b, c = st.columns(3)
                a.metric('PARI / 0–100', f'{current.PARI:.2f}')
                b.metric('Recent direction', direction, f'{change:+.2f} points / {bars} bars', delta_color='off')
                c.metric('SPY close', f'${current.Close:.2f}')
                st.subheader('The direction at a glance')
                count = st.select_slider('Chart window', options=[30,60,120,240], value=60)
                st.altair_chart(trend_chart(valid, count), use_container_width=True)
                st.caption('Actual PARI readings. Dashed line = 50. Fixed 0–100 scale keeps small moves in perspective. Bars are evenly spaced across session breaks; hover for timestamps. Color describes the net change across the visible window.')
                with st.expander('Distribution & underlying readings'):
                    histogram = pd.cut(valid.PARI, bins=range(0, 101, 5), include_lowest=True).value_counts(sort=False)
                    st.bar_chart(pd.DataFrame({'Readings': histogram.values}, index=[str(x) for x in histogram.index]), color='#21c9ab')
                    st.dataframe(valid.tail(30), use_container_width=True)
                st.caption('Yahoo prices may be delayed. Refresh manually for new completed candles.')
                st.download_button('Download calculated PARI CSV', df.to_csv().encode(), f'SPY_PARI_{frame.replace(" ", "_")}.csv', 'text/csv')
        except Exception as exc:
            st.error(str(exc))
    with st.expander('How to read PARI'):
        st.write('Snapshot guide: rising/falling means a change greater than ±2 PARI points over the last five bars; otherwise flat. Lean bullish requires a score above 50, positive 10-bar price momentum and rising PARI. Defensive requires the reverse. Other combinations call for patience or confirmation. These display rules are unvalidated heuristics, not a change to the PARI formula.')
        st.markdown('**PARI = 50 + 50 × momentum percentile − 50 × volatility percentile**')
        st.write('Momentum is close minus the close 10 bars earlier. Volatility is the standard deviation of the last 10 bar returns. Trend persistence is the mean of those returns; it is displayed as context and is not included in your original score.')
        st.write('Above 50 means the momentum percentile exceeds the volatility percentile; below 50 means the reverse. This is a relative price-action reading, not a trade recommendation or a validated probability. A high reading does not necessarily mean momentum is positive. Values near 20 or 80 do not establish that a major move is coming.')
        st.write('The original code ranks the entire loaded history. Adding prices can change earlier scores, so these historical charts are retrospective and must not be used as a look-ahead-free backtest.')
        st.write('Daily uses 10 daily bars. Intraday uses 10 bars of the selected length, spanning multiple sessions when necessary. Automatic aggregation starts at 9:30 a.m. New York time and excludes incomplete blocks, including shortened session-end blocks. The 4-hour view therefore typically has one complete bar per regular session.')


