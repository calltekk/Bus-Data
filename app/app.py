import os, json, yaml, time
import pandas as pd
import numpy as np
import pydeck as pdk
import streamlit as st

from logic import (
    normalize_disruptions,
    estimate_headway_minutes,
    aggregate_costs
)
from tfl_client import get_bus_disruptions, get_line_arrivals
from storage import read_table

st.set_page_config(page_title="Bus Disruption Cost Dashboard", layout="wide")

# --- Load config
CFG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
CFG = yaml.safe_load(open(CFG_PATH))

# --- Sidebar controls
st.sidebar.header("Controls & Assumptions")
cost_per_min = st.sidebar.number_input(
    "Cost per bus-minute (£)", min_value=0.5, max_value=5.0, value=float(CFG["costs"]["cost_per_bus_minute_gbp"]), step=0.1
)

sev_map = CFG["delays"]["severity_to_delay_minutes"]
for sev in list(sev_map.keys()):
    sev_map[sev] = st.sidebar.number_input(f"Delay per bus if {sev} (min)", 1, 30, int(sev_map[sev]), 1)

default_lines = st.sidebar.multiselect(
    "Watchlist lines", options=CFG["ui"]["default_lines"], default=CFG["ui"]["default_lines"]
)

st.sidebar.caption("Tip: Tweak assumptions live — costs update instantly.")

st.title("🚌 Bus Disruption Cost Dashboard")
st.caption("Quantifying the £ impact of live disruptions on TfL bus routes (demo)")

# --- Fetch disruptions (live; fallback to local sample)
with st.spinner("Fetching disruptions..."):
    try:
        raw_disruptions = get_bus_disruptions()
    except Exception:
        sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_disruptions.json")
        raw_disruptions = json.load(open(sample_path))
        st.warning("Using sample disruptions (offline mode).")

df_disr = normalize_disruptions(raw_disruptions)

# --- Headway estimations per line
st.subheader("Headway estimation (live arrivals → typical minutes between buses)")
line_ids = sorted(list(set([x for x in (default_lines or [])] + [x for x in df_disr["lineId"].dropna().unique().tolist()])))

line_to_headway = {}
progress = st.progress(0.0, text="Estimating headways...")
for i, lid in enumerate(line_ids):
    try:
        arr = get_line_arrivals(lid)
    except Exception:
        # offline fallback to saved sample if present
        sample_file = os.path.join(os.path.dirname(__file__), "data", f"sample_arrivals_line{lid}.json")
        if os.path.exists(sample_file):
            arr = json.load(open(sample_file))
        else:
            arr = []
    hw = estimate_headway_minutes(arr, CFG["headway"]["min_headway_minutes"], CFG["headway"]["max_headway_minutes"])
    line_to_headway[lid] = hw
    progress.progress((i+1)/max(1,len(line_ids)), text=f"Line {lid}: {hw:.1f} min")

progress.empty()

# --- Aggregate cost per route (by severity)
df_costs = aggregate_costs(df_disr, line_to_headway, sev_map, cost_per_min)

# KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Active disruptions", int(df_disr.shape[0]))
col2.metric("Lines impacted", int(df_costs["lineId"].nunique()) if not df_costs.empty else 0)
col3.metric("Estimated £/hour impact", f"£{df_costs['cost_per_hour_gbp'].sum():,.0f}" if not df_costs.empty else "£0")

# --- Table: cost by line & severity
st.subheader("£/hour impact by line & severity")
if df_costs.empty:
    st.info("No disruptions affecting bus lines at the moment (or data unavailable).")
else:
    st.dataframe(df_costs, use_container_width=True)

# --- Map (optional; requires lat/lon — many line disruptions don’t include it reliably)
# If you later add a join to roadworks points, you can visualize here with pydeck

st.divider()
with st.expander("Assumptions & Method"):
    st.markdown("""
- **How costs are computed**:
    - For each impacted line, we estimate **headway (minutes)** from live arrivals.
    - We map **severity → delay per bus** (editable above).
    - **Buses/hour ≈ 60 / headway**.  
    - **£/hour = delay_per_bus × buses/hour × cost_per_bus_minute**.
- **Why this matters**: Delay minutes increase **driver time, fuel burn**, and risk **TfL performance penalties** — this puts a *£* figure on where to intervene *right now*.
- **Tuning**: Adjust the sliders to reflect your cost model or internal assumptions.
""")
