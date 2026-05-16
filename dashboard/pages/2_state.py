"""State Results page — party breakdown + constituency table."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from dashboard.utils import ELECTION_ID, STATE_NAMES, api_get, page_header

page_header("🗺️ State Results", "Select a state to explore party & constituency results")

# ------------------------------------------------------------------
# State selector — pre-selects when navigated from the Home page
# ------------------------------------------------------------------
_codes = list(STATE_NAMES.keys())
_default = st.session_state.get("state_selector", _codes[0])
_default_idx = _codes.index(_default) if _default in _codes else 0

state_code = st.selectbox(
    "Select State",
    options=_codes,
    format_func=lambda c: STATE_NAMES[c],
    index=_default_idx,
    key="state_selector",
)

data = api_get(f"/states/{state_code}", params={"election_id": ELECTION_ID})
if not data:
    st.stop()

state = data["state"]
summary = data.get("summary")
party_results = data.get("party_results", [])

# ------------------------------------------------------------------
# KPI row
# ------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("State", state["name"])
with col2:
    st.metric("Total ACs", state["total_ac"])
with col3:
    declared = summary["ac_declared"] if summary else 0
    st.metric("Results Declared", declared)

st.divider()

# ------------------------------------------------------------------
# Party-wise horizontal bar chart
# ------------------------------------------------------------------
if party_results:
    st.subheader(f"Party-wise Seats — {state['name']}")
    parties = [r["party"]["abbreviation"] for r in party_results[:15]]
    seats = [r["total_seats"] for r in party_results[:15]]

    fig = px.bar(
        x=seats,
        y=parties,
        orientation="h",
        labels={"x": "Seats", "y": "Party"},
        color=seats,
        color_continuous_scale="Blues",
        text=seats,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=max(350, len(parties) * 30),
        margin=dict(l=80, r=40, t=20, b=20),
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Constituency table with search
# ------------------------------------------------------------------
st.subheader(f"Constituency Results — {state['name']}")
search = st.text_input("Search constituency name", key="constituency_search")
page = st.number_input("Page", min_value=1, value=1, step=1, key="constituency_page")
page_size = 50

constituencies_resp = api_get(
    "/constituencies/",
    params={
        "state_code": state_code,
        "election_id": ELECTION_ID,
        "search": search or None,
        "page": page,
        "page_size": page_size,
    },
)

if constituencies_resp:
    total = constituencies_resp.get("total", 0)
    items = constituencies_resp.get("items", [])
    st.caption(f"Showing {len(items)} of {total} constituencies")

    table_rows = []
    for item in items:
        c = item.get("constituency", {})
        winner = item.get("winner") or {}
        winner_party = item.get("winner_party") or {}
        runner = item.get("runner_up") or {}
        table_rows.append(
            {
                "AC#": c.get("ac_number", ""),
                "Constituency": c.get("name", ""),
                "Winner": winner.get("name", ""),
                "Party": winner_party.get("abbreviation", ""),
                "Runner-up": runner.get("name", ""),
                "Margin": item.get("margin", ""),
                "Status": item.get("status", ""),
            }
        )

    if table_rows:
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No constituencies found.")
