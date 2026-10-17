"""WARI reader page. No synthetic score or unverified baseline."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent


def render():
    st.markdown('<h1 class="rambo-title">WARI 🐋</h1>', unsafe_allow_html=True)
    st.markdown('### Is the big money splashing around, or getting out of the pool?')
    st.write('The Whale Alert Risk Indicator compares options activity with a historical baseline. PARI watches price. WARI asks what changed in the whale activity behind it.')
    st.markdown('<div class="card"><div class="soon-label">THE WHALE WEATHER REPORT</div><h3>Still on the research bench 🔧</h3><p class="muted">There isn’t a verified WARI reading to publish yet. The original research is back in the workshop, and this is where the finished reading will live.</p></div>', unsafe_allow_html=True)
    st.markdown('**What goes into the whale soup?**')
    cols = st.columns(2)
    items = [('🩸 Put share', 'How much of the recorded activity is puts.'), ('🐋 Big orders', 'How often orders reach 1,000 contracts.'), ('⏱️ Near-term action', 'Contracts with 30 days or less until expiry.'), ('🔭 Longer bets', 'Contracts with more than 30 days until expiry.'), ('💰 Put premium', 'Dollars recorded in put activity.'), ('📅 CPI activity', 'Activity on confirmed CPI dates, when that version of the model is used.')]
    for i, (title, description) in enumerate(items):
        with cols[i % 2].container(border=True):
            st.markdown('**'+title+'**')
            st.caption(description)
    st.write('More puts can reflect hedging, speculation or a larger position we cannot see. WARI needs a consistent sample and a tested formula before a number earns a bullish or bearish label.')
    with st.expander('What is being checked before WARI graduates?'):
        st.write('The saved methodology contains two different models. The later model’s weights do not reproduce a 1.00 baseline, and its put-share term points in the opposite direction from its written interpretation. The historical date filters also need to use each year’s own dates. We will resolve those differences against the original data, without forcing a historical result.')
    with st.container(key='milt_wari'):
        with st.expander('milt stuff'):
            st.caption('Original 2023/2024 baseline exports and a comparable current sample are needed. No score is calculated from the selected RAMBO filters: those are a different, narrower sample.')
