"""Interactive month view over the same verified RAMBO matches as the main board."""
import calendar
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from rambo import match

ROOT = Path(__file__).parent


def month_events(events, year, month):
    start = date(year, month, 1).isoformat()
    end = date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    return [e for e in events if e['date'] <= end and e.get('end_date', e['date']) >= start]


def render(data, company_heading):
    st.markdown('<h1 class="rambo-title">RAMBO Calendar</h1>', unsafe_allow_html=True)
    st.markdown('**Your catalyst fridge calendar. Minus the dentist appointment.**')
    st.caption('Click a day to open its events, matching contracts and official sources. Dates follow the company’s published calendar; times retain their stated timezone.')
    now = pd.Timestamp.now(tz='America/Los_Angeles').date()
    if 'rambo_month' not in st.session_state:
        st.session_state.rambo_month = now.replace(day=1)
    left, center, right = st.columns([1, 3, 1])
    first = st.session_state.rambo_month
    if left.button('← Previous', key='calendar_prev', width='stretch'):
        st.session_state.rambo_month = (first - timedelta(days=1)).replace(day=1)
        st.rerun()
    if right.button('Next →', key='calendar_next', width='stretch'):
        st.session_state.rambo_month = (first + timedelta(days=32)).replace(day=1)
        st.rerun()
    center.subheader(first.strftime('%B %Y'))
    a, b = st.columns([3, 1])
    ticker = a.selectbox('Company', ['All tickers'] + sorted({e['ticker'] for e in data['events']}))
    if b.button('Back to this month', width='stretch'):
        st.session_state.rambo_month = now.replace(day=1)
        st.rerun()
    # Include past months for review; match() still enforces confirmed, non-earnings and flow overlap.
    events = match(data['events'], data['prints'], first.isoformat())
    events = month_events(events, first.year, first.month)
    if ticker != 'All tickers':
        events = [e for e in events if e['ticker'] == ticker]
    st.caption('📞 Calls spotted · 🩸 Puts spotted · 🔀 Both · A calendar match is a research lead, not proof of why somebody traded.')
    for col, name in zip(st.columns(7), ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
        col.markdown('**' + name + '**')
    for week in calendar.Calendar().monthdatescalendar(first.year, first.month):
        for col, day in zip(st.columns(7), week):
            with col.container(border=True, height=175):
                if day.month != first.month:
                    st.caption(str(day.day))
                    continue
                hits = [e for e in events if e['date'] <= day.isoformat() <= e.get('end_date', e['date'])]
                if st.button(('📍 ' if day == now else '') + str(day.day) + (f' · {len(hits)}' if hits else ''), key='cal_'+day.isoformat(), width='stretch', help='Open events for '+day.isoformat()):
                    st.session_state.rambo_day = day.isoformat()
                for symbol in dict.fromkeys(e['ticker'] for e in hits):
                    asset = ROOT/'assets'/(symbol.lower()+'-logo.png')
                    if asset.exists():
                        st.image(str(asset), width=28)
                    st.markdown('**$'+symbol+'**')
    selected = st.session_state.get('rambo_day')
    if not selected or selected[:7] != first.strftime('%Y-%m'):
        selected = next((e['date'] if e['date'] >= first.isoformat() else first.isoformat() for e in events), first.isoformat())
    st.subheader('On the board · '+date.fromisoformat(selected).strftime('%B %d'))
    hits = [e for e in events if e['date'] <= selected <= e.get('end_date', e['date'])]
    if not hits:
        st.info('No matched RAMBOs on this day. Click another date.')
    for i, event in enumerate(hits):
        with st.container(border=True):
            st.markdown(company_heading(event['ticker']), unsafe_allow_html=True)
            st.subheader(event['title'])
            st.write(f"📅 {event['date']} → {event['end_date']} · {event.get('time', 'Time not announced')}")
            st.caption(event['category']+' · Verified '+event.get('verified_on', 'date not recorded'))
            st.write(event['summary'])
            st.write(event.get('note', ''))
            st.link_button('Read the official source ↗', event['url'])
            frame = pd.DataFrame(event['prints'])
            fields = ['date','time','underlying_symbol','strike','type','expiry','side','premium','size','filters']
            st.dataframe(frame[[c for c in fields if c in frame]], hide_index=True, width='stretch')
    st.caption('Saved flow: '+str(data.get('flow_imported_at', 'Timestamp unavailable')))
