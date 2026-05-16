"""Streamlit multi-page app entrypoint."""

import sys
from pathlib import Path

# Ensure project root is on sys.path so pages can import dashboard.utils, config, etc.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

st.set_page_config(
    page_title="ECI Election Results Portal",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigation
home = st.Page("pages/1_home.py", title="Home Dashboard", icon="🏠", default=True)
state_page = st.Page("pages/2_state.py", title="State Results", icon="🗺️")
constituency_page = st.Page("pages/3_constituency.py", title="Constituency Detail", icon="📍")
party_page = st.Page("pages/4_party_analytics.py", title="Party Analytics", icon="🎯")
trends_page = st.Page("pages/5_trends.py", title="Trends & Insights", icon="📊")

pg = st.navigation([home, state_page, constituency_page, party_page, trends_page])
pg.run()
