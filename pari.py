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

def render():
    import streamlit as st
    st.title('PARI')
    st.write('Your price-action risk indicator. Compare SPY momentum and volatility across five timeframes using the original formula.')
    frame = st.radio('Timeframe', list(FRAMES), horizontal=True)
    source = st.radio('Price source', ['Yahoo SPY', 'Upload price CSV'], horizontal=True)
    st.caption('Daily: five years of Yahoo history. Intraday: one month of 5-minute history, aggregated into complete regular-session bars. Each timeframe has its own ranking history; scores are not directly calibrated across timeframes.')
    close = None
    if source == 'Upload price CSV':
        st.caption('Upload prices already at the selected timeframe. Daily historical prices cannot produce intraday readings. CSV requires Date and Close; intraday dates must include times. Upload only completed candles.')
        upload = st.file_uploader('SPY price history', type=['csv'], key='pari_csv_' + frame)
        if upload:
            try:
                close = read_csv(upload)
                if frame != 'Daily' and (close.index == close.index.normalize()).all():
                    raise ValueError('This appears to be daily data. Intraday readings require intraday candles.')
            except Exception as exc:
                st.error(str(exc))
    else:
        @st.cache_data(ttl=300, show_spinner=False)
        def load(selected):
            return yahoo(selected)
        if st.button('Load / refresh prices', type='primary'):
            load.clear()
            st.session_state['pari_load'] = True
        if st.session_state.get('pari_load'):
            try:
                with st.spinner('Loading SPY prices…'):
                    close = load(frame)
            except Exception:
                st.error('Yahoo prices could not be loaded. Retry or upload an actual price CSV. No reading is substituted.')
    if close is not None:
        try:
            df = calculate(close)
            valid = df.dropna(subset=['PARI'])
            if valid.empty:
                st.warning('At least 11 valid closes are needed for a PARI reading.')
            else:
                current = valid.iloc[-1]
                prior = valid.iloc[-2].PARI if len(valid) > 1 else current.PARI
                a, b, c = st.columns(3)
                a.metric('Latest PARI', f'{current.PARI:.2f}', f'{current.PARI-prior:+.2f} vs prior bar')
                b.metric('SPY close', f'${current.Close:.2f}')
                c.metric('Calculated readings', len(valid))
                st.caption(f'Latest bar timestamp: {valid.index[-1]} • Dates are candle start times. Yahoo may delay prices; this is not a streaming feed.')
                st.line_chart(valid[['PARI']], color='#81e62b')
                histogram = pd.cut(valid.PARI, bins=range(0, 101, 5), include_lowest=True).value_counts(sort=False)
                st.subheader('Actual historical distribution')
                st.bar_chart(pd.DataFrame({'Readings': histogram.values}, index=[str(x) for x in histogram.index]), color='#21c9ab')
                st.dataframe(valid.tail(30), use_container_width=True)
                st.download_button('Download calculated PARI CSV', df.to_csv().encode(), f'SPY_PARI_{frame.replace(" ", "_")}.csv', 'text/csv')
        except Exception as exc:
            st.error(str(exc))
    with st.expander('How PARI works', expanded=True):
        st.markdown('**PARI = 50 + 50 × momentum percentile − 50 × volatility percentile**')
        st.write('Momentum is close minus the close 10 bars earlier. Volatility is the standard deviation of the last 10 bar returns. Trend persistence is the mean of those returns; it is displayed as context and is not included in your original score.')
        st.write('Above 50 means the momentum percentile exceeds the volatility percentile; below 50 means the reverse. This is a relative price-action reading, not a trade recommendation or a validated probability. A high reading does not necessarily mean momentum is positive. Values near 20 or 80 do not establish that a major move is coming.')
        st.write('The original code ranks the entire loaded history. Adding prices can change earlier scores, so these historical charts are retrospective and must not be used as a look-ahead-free backtest.')
        st.write('Daily uses 10 daily bars. Intraday uses 10 bars of the selected length, spanning multiple sessions when necessary. Automatic aggregation starts at 9:30 a.m. New York time and excludes incomplete blocks, including shortened session-end blocks. The 4-hour view therefore typically has one complete bar per regular session.')
        st.caption('Your saved 37.08 example and its randomly generated distribution are not used here. Every plotted score comes from loaded prices.')
