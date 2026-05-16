"""Trends & Insights — margin analysis, status distribution, close contests."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils import ELECTION_ID, api_get, page_header

page_header("📊 Trends & Insights", "Margins, close contests, and result patterns")

# ------------------------------------------------------------------
# Top & Bottom Margins
# ------------------------------------------------------------------
col_l, col_r = st.columns(2)

top_margins = api_get("/analytics/top-margins", params={"election_id": ELECTION_ID, "limit": 15}) or []
close_contests = api_get("/analytics/closest-contests", params={"election_id": ELECTION_ID, "limit": 15}) or []

with col_l:
    st.subheader("Largest Winning Margins")
    if top_margins:
        fig_top = px.bar(
            x=[m["margin"] for m in top_margins],
            y=[f"{m['constituency_name']} ({m['state_name'][:2]})" for m in top_margins],
            orientation="h",
            color=[m["winner_party"] for m in top_margins],
            labels={"x": "Margin (votes)", "y": ""},
            text=[f"{m['margin']:,}" for m in top_margins],
        )
        fig_top.update_traces(textposition="outside")
        fig_top.update_layout(
            height=450,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=180, r=40, t=10, b=10),
            showlegend=True,
        )
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.info("No margin data available.")

with col_r:
    st.subheader("Closest Contests")
    if close_contests:
        fig_close = px.bar(
            x=[m["margin"] for m in close_contests],
            y=[f"{m['constituency_name']} ({m['state_name'][:2]})" for m in close_contests],
            orientation="h",
            color=[m["winner_party"] for m in close_contests],
            labels={"x": "Margin (votes)", "y": ""},
            text=[f"{m['margin']:,}" for m in close_contests],
            color_discrete_sequence=px.colors.qualitative.Pastel,
        )
        fig_close.update_traces(textposition="outside")
        fig_close.update_layout(
            height=450,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=180, r=40, t=10, b=10),
            showlegend=True,
        )
        st.plotly_chart(fig_close, use_container_width=True)
    else:
        st.info("No contest data available.")

st.divider()

# ------------------------------------------------------------------
# State-wise seat declaration progress
# ------------------------------------------------------------------
st.subheader("Declaration Progress by State")
summaries = api_get("/analytics/state-summaries", params={"election_id": ELECTION_ID}) or []
if summaries:
    fig_prog = go.Figure()
    for s in summaries:
        pct = round(s["ac_declared"] / s["total_ac"] * 100, 1) if s["total_ac"] else 0
        fig_prog.add_trace(
            go.Bar(
                name=s["state_name"],
                x=[s["state_name"]],
                y=[pct],
                text=[f"{pct}%"],
                textposition="outside",
            )
        )
    fig_prog.update_layout(
        yaxis=dict(title="% Declared", range=[0, 110]),
        height=350,
        showlegend=False,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig_prog, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------
st.subheader("Top Margins Table")
if top_margins:
    st.dataframe(
        [
            {
                "State": m["state_name"],
                "Constituency": m["constituency_name"],
                "Winner": m["winner_name"],
                "Party": m["winner_party"],
                "Margin": f"{m['margin']:,}",
            }
            for m in top_margins
        ],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Closest Contests Table")
if close_contests:
    st.dataframe(
        [
            {
                "State": m["state_name"],
                "Constituency": m["constituency_name"],
                "Winner": m["winner_name"],
                "Party": m["winner_party"],
                "Margin": f"{m['margin']:,}",
            }
            for m in close_contests
        ],
        use_container_width=True,
        hide_index=True,
    )
