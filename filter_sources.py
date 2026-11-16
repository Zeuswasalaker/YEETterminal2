"""Canonical user-provided Unusual Whales filter links, Nov 16 2026.
These links open the source; they do not claim an automatic feed refresh.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

SOURCES = [
    ("Orange Swan","Alerts","SMH/BABA/JD/SPY/QQQ, ask-side OTM, vol > OI","https://unusualwhales.com/option-flow-alerts?is_bid_side=false&is_multi_leg=false&is_otm=true&limit=250&min_ask_perc=0.7&min_dte=2&min_premium=10000&ticker_symbol=SMH%2CBABA%2CJD%2CSPY%2CQQQ&vol_greater_oi=true&watchlist_name=Orange%20Swan%20BETA"),
    ("SPY In the Money Magic","Alerts","SPY near-the-money flow, vol > OI","https://unusualwhales.com/option-flow-alerts?is_bid_side=false&is_multi_leg=false&is_otm=true&issue_types[]=ETF&issue_types[]=Index&limit=250&max_diff=0.005&min_dte=1&ticker_symbol=SPY&vol_greater_oi=true&watchlist_name=SPY%20In%20the%20Money%20Magic"),
    ("MEME SWAN","Alerts","Meme universe with SPY/QQQ/IWM benchmarks","https://unusualwhales.com/option-flow-alerts?is_bid_side=false&is_multi_leg=false&is_otm=true&limit=250&min_ask_perc=0.7&min_dte=2&min_premium=10000&ticker_symbol=SPY%2CQQQ%2CIWM%2CGME%2CDAN%2CHOOD%2CIREN%2CWEN%2CCRWV%2CSOUN%2CRIVN%2CAMC%2CHTZ%2CKOSS%2COPEN%2CBYND%2CDJT%2CPLTR%2CRKLB%2CACHR%2CLCID&vol_greater_oi=true&watchlist_name=MEME%20SWAN"),
    ("NEWS FINDER","Alerts","Low historic options volume, OTM, vol > OI","https://unusualwhales.com/option-flow-alerts?is_bid_side=false&is_multi_leg=false&is_otm=true&limit=250&max_dte=60&min_diff=0.05&rule_name[]=LowHistoricVolumeFloor&vol_greater_oi=true&watchlist_name=NEWS%20FINDER"),
    ("NAUTILUS","Flow","Opening, >=3 vol/OI, premium >=$50k, DTE 8-40","https://unusualwhales.com/live-options-flow?show_stocks=true&floor_only=true&show_ask_side=true&show_china=true&min_dte=8&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&is_otm=true&is_single_leg=true&show_volatility=true&min_earnings_dte=14&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&volume_greater_oi=true&min_diff=0.07&ticker_symbol=-TMSTR%2CMS%2CNCOIN-MSTX%2CMSTU%2CTSLA%2CMSTR%2CNVDA%2C&hide_expired=false&min_premium=50000&min_ask_perc=0.75&max_dte=40&show_puts=true&limit=250&sweep_only=true&show_none=true&issue_types[]=Common%20Stock&issue_types[]=ADR&issue_types[]=ETF&show_calls=true&show_etfs=true&show_adr=true&max_iv=1.30&exclude_deep_itm=true&show_normal=true&show_dividend=false&order=Time&show_bid_side=false&show_indices=false&opening=true&show_earnings=true&is_multi_leg=false&min_vol_oi_ratio=3&cross_only=false&mid_side=false&add_agg_trades=true&watchlist_name=x%20NAUTILUS%20x"),
    ("FARCRY ULTRA","Flow","Opening, far-dated DTE 60-300, premium >=$50k","https://unusualwhales.com/live-options-flow?exclude_deep_itm=true&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&is_multi_leg=false&is_otm=true&issue_types[]=Common%20Stock&issue_types[]=ADR&issue_types[]=ETF&limit=250&max_dte=300&max_iv=1&min_ask_perc=0.75&min_diff=0.08&min_dte=60&min_earnings_dte=14&min_premium=50000&opening=true&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&volume_greater_oi=true&add_agg_trades=true&watchlist_name=FARCRY%20ULTRA"),
    ("PSU","Flow","Opening, >=5 vol/OI, premium >=$50k","https://unusualwhales.com/live-options-flow?show_stocks=true&floor_only=true&show_ask_side=true&show_china=true&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&is_otm=true&is_single_leg=true&show_volatility=true&min_earnings_dte=14&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&volume_greater_oi=true&min_diff=0.07&hide_expired=false&min_premium=50000&min_ask_perc=0.75&show_puts=true&limit=250&sweep_only=true&show_none=true&issue_types[]=Common%20Stock&issue_types[]=ADR&issue_types[]=ETF&show_calls=true&show_etfs=true&show_adr=true&show_normal=true&show_dividend=false&order=Time&show_bid_side=false&show_indices=false&opening=true&show_earnings=true&is_multi_leg=false&min_vol_oi_ratio=5&cross_only=false&mid_side=false&add_agg_trades=true&watchlist_name=PSU"),
    ("Weapons Free PSU","Flow",">=2 vol/OI, premium >=$25k, DTE <=90","https://unusualwhales.com/live-options-flow?show_stocks=true&floor_only=true&show_ask_side=true&show_china=true&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&excluded_tags[]=volatility&is_otm=true&is_single_leg=true&show_volatility=false&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&volume_greater_oi=true&min_diff=0.05&hide_expired=false&min_premium=25000&min_ask_perc=0.75&max_dte=90&show_puts=true&limit=250&sweep_only=true&show_none=true&issue_types[]=Common%20Stock&issue_types[]=ADR&show_calls=true&show_etfs=false&show_adr=true&show_normal=true&show_dividend=false&order=Time&show_bid_side=false&show_indices=false&show_earnings=true&is_multi_leg=false&min_vol_oi_ratio=2&cross_only=false&mid_side=false&add_agg_trades=true&watchlist_name=WF%20PSU"),
    ("BAT","Flow","OTM, DTE 30-90, premium >=$50k","https://unusualwhales.com/live-options-flow?exclude_deep_itm=true&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&hide_expired=true&is_multi_leg=false&is_otm=true&issue_types[]=Common%20Stock&issue_types[]=ADR&issue_types[]=ETF&limit=250&max_dte=90&max_iv=1&min_ask_perc=0.7&min_diff=0.08&min_dte=30&min_earnings_dte=14&min_premium=50000&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&ticker_symbol=-MSTR%2CCOIN&volume_greater_oi=true&add_agg_trades=true&watchlist_name=x%20BAT%20Filter%20x"),
    ("Freelance Ultra","Flow","OTM, DTE 14-60, premium >=$50k","https://unusualwhales.com/live-options-flow?add_agg_trades=true&exclude_deep_itm=true&excluded_tags[]=bid_side&excluded_tags[]=mid_side&excluded_tags[]=dividend&is_multi_leg=false&is_otm=true&issue_types[]=Common%20Stock&issue_types[]=ADR&issue_types[]=ETF&limit=250&max_dte=60&max_earnings_dte=60&max_iv=1.30&min_diff=0.07&min_dte=14&min_earnings_dte=10&min_premium=50000&min_volume=2&order=Time&report_flag[]=sweep&report_flag[]=floor&report_flag[]=normal&ticker_symbol=-TMSTR%2CMS%2CCOIN-MSTX%2CMSTU%2CTSLA%2CMSTR&volume_greater_oi=true&watchlist_name=Freelance%20Ultra"),

]

def render():
    st.markdown('<div class="eyebrow">THE YEET / SOURCES</div><h1>Filter Control</h1>', unsafe_allow_html=True)
    st.caption("Canonical Unusual Whales source links supplied November 16, 2026. These are the screens to use for the next import.")
    st.info("Source links are NOT a live data sync. The site's observed trades and performance remain at their last separately published capture until new verified exports are imported.")
    st.metric("Configured UW filters", len(SOURCES))
    for group in ("Alerts", "Flow"):
        st.subheader(group + " screens")
        for name, kind, explanation, url in SOURCES:
            if kind != group:
                continue
            with st.container(border=True):
                left, right = st.columns([4, 1], vertical_alignment="center")
                with left:
                    st.markdown(f"**{name}**")
                    st.caption(explanation)
                with right:
                    st.link_button("Open in UW ↗", url, use_container_width=True)
    st.caption("Actual alert dates, trade premiums and cross-filter matches must be verified from the source exports. Multiple screen appearances of the same economic order count once.")
