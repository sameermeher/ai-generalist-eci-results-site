"""Home Dashboard — KPI tiles + all-state overview."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.utils import STATE_NAMES, api_get, kpi_tile, page_header

page_header("🗳️ ECI Election Results — May 2026", "Final Results · All 824 Constituencies Declared")

# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------
summaries = api_get("/analytics/state-summaries") or []
party_data = api_get("/parties/") or []

# ------------------------------------------------------------------
# KPI row — total ACs declared
# ------------------------------------------------------------------
total_ac = sum(s["total_ac"] for s in summaries)
total_declared = sum(s["ac_declared"] for s in summaries)

col1, col2, col3, col4 = st.columns(4)
with col1:
    kpi_tile("Total Constituencies", total_ac)
with col2:
    kpi_tile("Results Declared", total_declared)
with col3:
    kpi_tile("States Covered", len(summaries))
with col4:
    pct = round(total_declared / total_ac * 100, 1) if total_ac else 0
    kpi_tile("Completion %", f"{pct}%")

st.divider()

# ------------------------------------------------------------------
# State-wise completion bar
# ------------------------------------------------------------------
if summaries:
    st.subheader("Seats Declared by State")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Declared",
            x=[s["state_name"] for s in summaries],
            y=[s["ac_declared"] for s in summaries],
            marker_color="#1a3c5e",
            text=[s["ac_declared"] for s in summaries],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Total",
            x=[s["state_name"] for s in summaries],
            y=[s["total_ac"] for s in summaries],
            marker_color="#d3e4f5",
            text=[s["total_ac"] for s in summaries],
            textposition="outside",
        )
    )
    fig.update_layout(
        barmode="overlay",
        height=400,
        margin=dict(t=20, b=20),
        legend=dict(orientation="h"),
        xaxis_title="State",
        yaxis_title="Assembly Constituencies",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------------------
# Cross-state top parties table
# ------------------------------------------------------------------
if party_data:
    st.subheader("Top Parties — All States")

    # Clickable state navigation buttons — clicking a state opens the State Results page
    st.caption("Click a state name to see detailed results:")
    nav_cols = st.columns(len(STATE_NAMES))
    for col, (code, name) in zip(nav_cols, STATE_NAMES.items()):
        with col:
            if st.button(f"📍 {name}", key=f"nav_{code}", use_container_width=True):
                # Pre-select state in the selectbox on the State Results page
                st.session_state["state_selector"] = code
                st.switch_page("pages/2_state.py")

    st.write("")

    # Build a tidy DataFrame — state columns use readable names
    top_15 = party_data[:15]
    df_rows = []
    for p in top_15:
        row = {"Party": p["abbreviation"], "Full Name": p["party_name"]}
        for code, state_name in STATE_NAMES.items():
            row[state_name] = p["results"].get(code, 0)
        row["Total"] = p["grand_total"]
        df_rows.append(row)

    df = pd.DataFrame(df_rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Party": st.column_config.TextColumn("Party", width="small"),
            "Full Name": st.column_config.TextColumn("Full Name", width="medium"),
            "Total": st.column_config.NumberColumn("Total", format="%d"),
            **{
                name: st.column_config.NumberColumn(name, format="%d")
                for name in STATE_NAMES.values()
            },
        },
    )
