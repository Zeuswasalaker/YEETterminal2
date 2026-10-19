"""Reader-facing, curated release history."""
import streamlit as st

RELEASES = [
    ('October 19, 2026', 'Morning receipts and a broader WARI capture', [
        ('🥇 Two published 770 calls reached ITM', 'The October 20 and October 22 SPY 770 calls are retired from the active board after an observed 770.01 quote at 08:27:26 Pacific. This confirms an ITM touch, not a trading return or an opening-bell fill.'),
        ('🐋 Index WARI refreshed', 'A partial-session capture through 11:55 Pacific contains 270 distinct alert rows. The score is 13/100: little disagreement, with a mild put-heavy flow versus rising SPY mismatch. Historical price volatility provides the price baseline; the flow reference is neutral 50%, not a calibrated broad-SPY flow baseline.'),
        ('🔎 Refresh coverage', 'The remaining filter scans, Orange Swan refresh and complete new RAMBO confirmation are pending restored source access. Existing sections retain their prior timestamps.')]),
    ('October 17, 2026', 'More ways to find your next rabbit hole', [
        ('📅 RAMBO Calendar', 'A clickable monthly board with company badges, multi-day events, matching contracts and official sources. Use the arrows to browse months or narrow it to your ticker.'),
        ('🐋 WARI gets a home', 'The Whale Alert Risk Indicator now has its own explainer page. A current score stays off the board until the historical inputs and formula are verified.'),
        ('📝 This very page', 'A running list of what changed, so you do not have to play spot-the-difference with the Terminal.')]),
    ('October 16, 2026', 'A cleaner Prestige board', [
        ('🥇 In the money, off the active board', 'Saved SPY price checks retire qualifying Prestige contracts once they move in the money after activation. Their history stays saved. Reaching the strike is not the same as a verified trading profit.')]),
]


def render():
    st.markdown('<h1 class="rambo-title">What’s new?</h1>', unsafe_allow_html=True)
    st.markdown('**The Terminal keeps growing. Here’s what we bolted on.**')
    for day, title, changes in RELEASES:
        with st.container(border=True):
            st.caption(day)
            st.subheader(title)
            for name, description in changes:
                st.markdown('**'+name+'**')
                st.write(description)
    st.caption('Feature releases live here. Individual flow refreshes and event checks keep their own timestamps on the relevant boards.')

