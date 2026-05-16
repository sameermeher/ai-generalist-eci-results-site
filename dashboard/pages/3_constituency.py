"""Constituency Detail — candidate breakdown, vote bar, pie chart."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import streamlit as st

from dashboard.utils import ELECTION_ID, STATE_NAMES, api_get, page_header

page_header("📍 Constituency Detail", "Candidate-level vote breakdown")

# ------------------------------------------------------------------
# Selection: state → constituency
# ------------------------------------------------------------------
state_code = st.selectbox(
    "State", options=list(STATE_NAMES.keys()), format_func=lambda c: STATE_NAMES[c]
)

constituencies_resp = api_get(
    "/constituencies/",
    params={"state_code": state_code, "election_id": ELECTION_ID, "page_size": 300},
)

if not constituencies_resp or not constituencies_resp.get("items"):
    st.info("No constituency data found. Run the ETL pipeline first.")
    st.stop()

items = constituencies_resp["items"]
constituency_options = {
    item["constituency"]["id"]: f"AC-{item['constituency']['ac_number']} {item['constituency']['name']}"
    for item in items
}

selected_id = st.selectbox(
    "Constituency",
    options=list(constituency_options.keys()),
    format_func=lambda k: constituency_options[k],
)

detail = api_get(f"/constituencies/{selected_id}")
if not detail:
    st.stop()

constituency = detail["constituency"]
result = detail.get("result") or {}
candidates = detail.get("candidates", [])

# ------------------------------------------------------------------
# Summary KPIs
# ------------------------------------------------------------------
st.subheader(f"AC-{constituency['ac_number']} — {constituency['name']}")
col1, col2, col3, col4 = st.columns(4)

winner = result.get("winner") or {}
winner_party = result.get("winner_party") or {}
with col1:
    st.metric("Winner", winner.get("name", "—"))
with col2:
    st.metric("Party", winner_party.get("abbreviation", "—"))
with col3:
    st.metric("Margin", f"{result.get('margin', 0):,}" if result.get("margin") else "—")
with col4:
    rounds = result.get("rounds_counted", 0)
    total_r = result.get("total_rounds", 0)
    st.metric("Rounds", f"{rounds}/{total_r}" if total_r else "—")

st.caption(f"Status: **{result.get('status', 'Unknown')}**")
st.divider()

if not candidates:
    st.info("Candidate-level data not yet available. Run ETL with candidate scraping enabled.")
    st.stop()

# Build display data
cand_names = [c["candidate"]["name"] for c in candidates]
cand_votes = [c["votes"] for c in candidates]
cand_parties = [
    (c["candidate"].get("party") or {}).get("abbreviation", "IND") for c in candidates
]

# ------------------------------------------------------------------
# Bar chart — votes per candidate
# ------------------------------------------------------------------
st.subheader("Votes by Candidate")
fig_bar = px.bar(
    x=cand_votes,
    y=cand_names,
    orientation="h",
    color=cand_parties,
    labels={"x": "Votes", "y": "Candidate", "color": "Party"},
    text=[f"{v:,}" for v in cand_votes],
)
fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(
    height=max(350, len(cand_names) * 30),
    yaxis=dict(autorange="reversed"),
    margin=dict(l=160, r=40, t=20, b=20),
    showlegend=True,
)
st.plotly_chart(fig_bar, use_container_width=True)

# ------------------------------------------------------------------
# Pie chart — vote share
# ------------------------------------------------------------------
st.subheader("Vote Share")
fig_pie = px.pie(
    names=cand_names,
    values=cand_votes,
    color=cand_parties,
    hole=0.35,
)
fig_pie.update_traces(textinfo="label+percent")
fig_pie.update_layout(height=420, margin=dict(t=20, b=20))
st.plotly_chart(fig_pie, use_container_width=True)

# ------------------------------------------------------------------
# Candidate table
# ------------------------------------------------------------------
st.subheader("Candidate Results Table")
table = [
    {
        "Pos": c["position"],
        "Candidate": c["candidate"]["name"],
        "Party": cand_parties[i],
        "Votes": f"{c['votes']:,}",
        "Winner": "✓" if c["is_winner"] else "",
    }
    for i, c in enumerate(candidates)
]
st.dataframe(table, use_container_width=True, hide_index=True)
