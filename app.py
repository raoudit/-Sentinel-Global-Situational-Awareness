"""
Sentinel — Open-Source Intelligence (OSINT) Threat Dashboard
A Palantir-Gotham-style situational awareness dashboard built entirely on
free, public data sources (GDELT Project). No private, classified, or
restricted data is used anywhere in this project.

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

from data_source import fetch_events, compute_risk_scores, EVENT_TYPES
from entity_graph import build_entity_graph, graph_to_plotly_elements
from trend_analysis import fetch_volume_timeline, analyze

# ---------------------------------------------------------------------------
# PAGE CONFIG + THEME
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SENTINEL // OSINT Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = """
<style>
    .stApp { background-color: #0a0e14; color: #c9d1d9; }
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #1f2937; }
    h1, h2, h3 { font-family: 'Courier New', monospace; color: #00e5ff; letter-spacing: 1px; }
    .metric-box {
        background: #10151c; border: 1px solid #1f2937; border-radius: 6px;
        padding: 14px 18px; text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #00e5ff; font-family: 'Courier New', monospace; }
    .metric-label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .feed-item {
        border-left: 3px solid #00e5ff; background: #10151c; padding: 8px 12px;
        margin-bottom: 6px; font-family: 'Courier New', monospace; font-size: 13px;
    }
    .feed-time { color: #8b949e; font-size: 11px; }
    .status-live { color: #3fb950; font-weight: bold; }
    .status-sample { color: #d29922; font-weight: bold; }
    div[data-testid="stDataFrame"] { background-color: #10151c; }
</style>
"""
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🛰️ SENTINEL CONTROL")
st.sidebar.markdown("---")

query = st.sidebar.text_input(
    "Search query (GDELT keywords)",
    value="conflict OR cyberattack OR protest",
    help="Keywords used to pull live open-source news events from the GDELT Project.",
)
max_records = st.sidebar.slider("Max events to pull", 20, 150, 75, step=5)
refresh = st.sidebar.button("🔄 Refresh live feed")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**About Sentinel**\n\n"
    "An open-source intelligence (OSINT) dashboard inspired by real-world "
    "situational-awareness platforms. It aggregates **public** news event data, "
    "geolocates it, computes a weighted risk score per region, and visualizes "
    "entity relationships — all using free, publicly available sources.\n\n"
    "**No private, classified, or restricted data is used.**"
)

# ---------------------------------------------------------------------------
# DATA FETCH (cached so we don't hit the API on every widget interaction)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_data(q, n):
    return fetch_events(query=q, max_records=n)

# The refresh button needs to actually invalidate the cache, otherwise it just
# reruns the script and Streamlit hands back the same cached result.
if refresh:
    load_data.clear()

with st.spinner("Pulling open-source event data..."):
    df, mode = load_data(query, max_records)

st.caption(f"Last pulled: {datetime.utcnow().strftime('%H:%M:%S UTC')} · cache refreshes automatically every 5 min, or click Refresh anytime")

risk_df = compute_risk_scores(df)

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
top_l, top_r = st.columns([3, 1])
with top_l:
    st.markdown("# 🛰️ SENTINEL — Global Situational Awareness")
    st.caption("Open-source intelligence dashboard · Public data only · Built for demonstration & educational purposes")
with top_r:
    status_class = "status-live" if mode == "live" else "status-sample"
    status_label = "● LIVE — GDELT feed" if mode == "live" else "● SAMPLE DATA (offline fallback)"
    st.markdown(f"<div class='metric-box'><span class='{status_class}'>{status_label}</span><br>"
                f"<span class='metric-label'>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</span></div>",
                unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# TOP METRICS ROW
# ---------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"<div class='metric-box'><div class='metric-value'>{len(df)}</div>"
                f"<div class='metric-label'>Tracked Events</div></div>", unsafe_allow_html=True)
with m2:
    st.markdown(f"<div class='metric-box'><div class='metric-value'>{df['country'].nunique()}</div>"
                f"<div class='metric-label'>Regions Monitored</div></div>", unsafe_allow_html=True)
with m3:
    top_country = risk_df.iloc[0]["country"] if not risk_df.empty else "N/A"
    st.markdown(f"<div class='metric-box'><div class='metric-value'>{top_country}</div>"
                f"<div class='metric-label'>Highest Risk Region</div></div>", unsafe_allow_html=True)
with m4:
    avg_sev = round(df["severity"].mean(), 1) if not df.empty else 0
    st.markdown(f"<div class='metric-box'><div class='metric-value'>{avg_sev}/10</div>"
                f"<div class='metric-label'>Avg Severity</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# MAP + RISK CHART
# ---------------------------------------------------------------------------
map_col, risk_col = st.columns([2, 1])

with map_col:
    st.markdown("### 🌍 Global Event Map")
    fig_map = px.scatter_geo(
        df, lat="lat", lon="lon",
        color="event_type", size="severity",
        hover_name="headline",
        hover_data={"country": True, "severity": True, "lat": False, "lon": False},
        projection="natural earth",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_map.update_layout(
        paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14",
        geo=dict(bgcolor="#0a0e14", showland=True, landcolor="#161b22",
                 showocean=True, oceancolor="#0a0e14",
                 showcountries=True, countrycolor="#30363d"),
        font=dict(color="#c9d1d9"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0), height=430,
    )
    st.plotly_chart(fig_map, use_container_width=True)

with risk_col:
    st.markdown("### ⚠️ Risk Score by Region")
    top_risk = risk_df.head(8)
    fig_bar = go.Figure(go.Bar(
        x=top_risk["risk_score_normalized"], y=top_risk["country"],
        orientation="h", marker=dict(color=top_risk["risk_score_normalized"], colorscale="Turbo"),
    ))
    fig_bar.update_layout(
        paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14",
        font=dict(color="#c9d1d9"), xaxis_title="Normalized Risk (0-100)",
        margin=dict(l=0, r=0, t=10, b=0), height=430,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# COVERAGE TREND & ANOMALY DETECTION (new capability)
# ---------------------------------------------------------------------------
st.markdown("### 📈 Coverage Trend & Anomaly Detection")
st.caption(
    "Daily volume of matching coverage over the last 14 days, with a short linear "
    "forecast and a statistical anomaly flag (z-score ≥ 1.5 vs. the recent baseline)."
)

@st.cache_data(ttl=600, show_spinner=False)
def load_timeline(q):
    return fetch_volume_timeline(q)

timeline_df, timeline_mode = load_timeline(query)
trend = analyze(timeline_df)

trend_col, banner_col = st.columns([3, 1])

with trend_col:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=timeline_df["date"], y=timeline_df["value"],
        mode="lines+markers", name="Actual coverage volume",
        line=dict(color="#00e5ff", width=2),
    ))
    if trend.get("has_forecast"):
        last_date = timeline_df["date"].iloc[-1]
        forecast_dates = [last_date + timedelta(days=i + 1) for i in range(len(trend["forecast_x"]))]
        fig_trend.add_trace(go.Scatter(
            x=forecast_dates, y=trend["forecast_y"],
            mode="lines+markers", name="Linear forecast",
            line=dict(color="#d29922", width=2, dash="dash"),
        ))
    fig_trend.update_layout(
        paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14", font=dict(color="#c9d1d9"),
        margin=dict(l=0, r=0, t=10, b=0), height=300,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with banner_col:
    mode_label = "LIVE" if timeline_mode == "live" else "SAMPLE"
    mode_class = "status-live" if timeline_mode == "live" else "status-sample"
    st.markdown(f"<div class='metric-box'><span class='{mode_class}'>● {mode_label}</span></div>", unsafe_allow_html=True)
    if trend.get("anomaly"):
        st.markdown(
            f"<div class='metric-box' style='border-color:#d29922; margin-top:8px;'>"
            f"<div class='metric-value' style='color:#d29922;'>⚠ ANOMALY</div>"
            f"<div class='metric-label'>z = {trend['z_score']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='metric-box' style='margin-top:8px;'>"
            f"<div class='metric-value' style='color:#3fb950;'>NORMAL</div>"
            f"<div class='metric-label'>z = {trend.get('z_score', 0)}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ---------------------------------------------------------------------------
# ENTITY GRAPH + LIVE FEED
# ---------------------------------------------------------------------------
graph_col, feed_col = st.columns([2, 1])

with graph_col:
    st.markdown("### 🔗 Entity Relationship Graph")
    st.caption("Countries linked when they share a recent event category — a simplified link-analysis view.")
    G = build_entity_graph(df)
    edge_x, edge_y, node_x, node_y, node_text, node_size = graph_to_plotly_elements(G)

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color="#30363d"),
                             hoverinfo="none", mode="lines")
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=node_text,
        textposition="top center", textfont=dict(color="#c9d1d9", size=10),
        marker=dict(size=node_size, color="#00e5ff", line=dict(width=1, color="#0a0e14")),
        hoverinfo="text",
    )
    fig_graph = go.Figure(data=[edge_trace, node_trace])
    fig_graph.update_layout(
        paper_bgcolor="#0a0e14", plot_bgcolor="#0a0e14",
        showlegend=False, margin=dict(l=0, r=0, t=10, b=0), height=420,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    st.plotly_chart(fig_graph, use_container_width=True)

with feed_col:
    st.markdown("### 📡 Live Event Feed")
    feed_df = df.sort_values("severity", ascending=False).head(12)
    for _, row in feed_df.iterrows():
        st.markdown(
            f"<div class='feed-item'>"
            f"<b>[{row['event_type'].upper()}]</b> {row['headline'][:70]}<br>"
            f"<span class='feed-time'>{row['country']} · severity {row['severity']}/10 · {row['source']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ---------------------------------------------------------------------------
# EXPORT INTELLIGENCE BRIEF (new capability)
# ---------------------------------------------------------------------------
top5 = "\n".join(
    f"{i+1}. {row['country']} — risk {row['risk_score_normalized']:.1f}/100"
    for i, (_, row) in enumerate(risk_df.head(5).iterrows())
)
brief = f"""SENTINEL INTELLIGENCE BRIEF
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Query: {query}
Data mode: {mode.upper()}

SUMMARY
- {len(df)} tracked events across {df['country'].nunique()} regions
- Highest risk region: {risk_df.iloc[0]['country'] if not risk_df.empty else 'N/A'}
- Average severity: {avg_sev}/10
- Coverage trend: {'ANOMALY DETECTED (z=' + str(trend.get('z_score', 0)) + ')' if trend.get('anomaly') else 'within normal range (z=' + str(trend.get('z_score', 0)) + ')'}

TOP 5 HIGHEST-RISK REGIONS
{top5}

--
Generated by Sentinel — an OSINT dashboard built on public data (GDELT Project).
Not affiliated with any government or defense agency. For educational/portfolio use.
"""
st.download_button("⬇ Export Intelligence Brief (.txt)", brief, file_name="sentinel_brief.txt", mime="text/plain")

st.markdown("---")

# ---------------------------------------------------------------------------
# RAW DATA TABLE (expandable)
# ---------------------------------------------------------------------------
with st.expander("📋 View raw event data table"):
    st.dataframe(
        df[["country", "event_type", "headline", "severity", "source"]],
        use_container_width=True, height=300,
    )


st.markdown(
    "<br><center><span style='color:#8b949e; font-size:12px;'>"
    "SENTINEL · Built with public data (GDELT Project) for educational/portfolio purposes · "
    "Not affiliated with any government or defense agency."
    "</span></center>",
    unsafe_allow_html=True,
)
