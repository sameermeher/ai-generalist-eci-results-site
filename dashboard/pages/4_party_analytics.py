"""Party Analytics — cross-state comparison, seat share donuts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils import ELECTION_ID, STATE_NAMES, api_get, page_header

page_header("🎯 Party Analytics", "Cross-state seat distribution and party performance")

party_data = api_get("/parties/", params={"election_id": ELECTION_ID}) or []
if not party_data:
    st.info("No party data available.")
    st.stop()

# ------------------------------------------------------------------
# Party selector (multi)
# ------------------------------------------------------------------
all_abbrs = [p["abbreviation"] for p in party_data]
default_top5 = all_abbrs[:5]
selected_parties = st.multiselect(
    "Select parties to compare", options=all_abbrs, default=default_top5
)
if not selected_parties:
    st.warning("Select at least one party.")
    st.stop()

filtered = [p for p in party_data if p["abbreviation"] in selected_parties]

# ------------------------------------------------------------------
# Cross-state grouped bar
# ------------------------------------------------------------------
st.subheader("Seats by State — Selected Parties")
state_codes = list(STATE_NAMES.keys())
fig_grouped = go.Figure()

colors = px.colors.qualitative.Set2
for i, p in enumerate(filtered):
    y_vals = [p["results"].get(code, 0) for code in state_codes]
    fig_grouped.add_trace(
        go.Bar(
            name=p["abbreviation"],
            x=[STATE_NAMES[c] for c in state_codes],
            y=y_vals,
            text=y_vals,
            textposition="outside",
            marker_color=colors[i % len(colors)],
        )
    )

fig_grouped.update_layout(
    barmode="group",
    height=420,
    margin=dict(t=20, b=20),
    legend=dict(orientation="h"),
    xaxis_title="State",
    yaxis_title="Seats Won",
)
st.plotly_chart(fig_grouped, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Seat share donuts — one per state
# ------------------------------------------------------------------
st.subheader("Seat Share per State")

cols = st.columns(len(state_codes))
for col, code in zip(cols, state_codes):
    # Get all party results for this state
    state_parties = sorted(
        [(p["abbreviation"], p["results"].get(code, 0)) for p in party_data],
        key=lambda x: x[1],
        reverse=True,
    )
    non_zero = [(name, seats) for name, seats in state_parties if seats > 0]
    if not non_zero:
        col.caption(f"{STATE_NAMES[code]}: No data")
        continue
    names, values = zip(*non_zero)
    fig_donut = go.Figure(
        go.Pie(
            labels=names,
            values=values,
            hole=0.4,
            textinfo="label+value",
            showlegend=False,
        )
    )
    fig_donut.update_layout(
        title=dict(text=STATE_NAMES[code], x=0.5),
        height=300,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    col.plotly_chart(fig_donut, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Party total ranking table
# ------------------------------------------------------------------
st.subheader("Overall Rankings")
ranking = [
    {"Party": p["abbreviation"], "Full Name": p["party_name"], "Total Seats": p["grand_total"]}
    for p in party_data
]
st.dataframe(ranking[:30], use_container_width=True, hide_index=True)
