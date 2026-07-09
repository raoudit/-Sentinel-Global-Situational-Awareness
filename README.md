# 🛰️ Sentinel — Open-Source Intelligence (OSINT) Dashboard

**🔗 Live demo:** [sentinel-global-situational-awareness.streamlit.app](https://sentinel-global-situational-awareness-bclf3l9hpj2iwqctcd9f5t.streamlit.app/)

Sentinel is a real-time situational-awareness dashboard inspired by intelligence
analysis platforms like Palantir Gotham — built entirely on **free, public data
sources**. It pulls open-source news event data, maps it geographically, scores
regions by risk, tracks whether coverage of a topic is trending up, flat, or
spiking, and visualizes relationships between countries using a network graph.

> ⚠️ **This is an educational/portfolio project.** It uses only public news data
> (via the [GDELT Project](https://www.gdeltproject.org/)) and is not affiliated
> with any government, defense, or intelligence agency.

## Features

- **🌍 Global Event Map** — plots recent world events (conflict, cyber incidents,
  civil unrest, natural disasters, etc.) on an interactive world map
- **⚠️ Risk Scoring Engine** — computes a weighted risk score per country/region
  based on event type and severity
- **📈 Coverage Trend & Anomaly Detection** *(new)* — pulls a 14-day daily
  coverage-volume timeline from GDELT's `TimelineVolRaw` mode, fits a linear
  trend, projects a 2-day forecast, and flags the latest day as anomalous if
  it deviates 1.5+ standard deviations from the recent baseline (a real
  z-score check, not a black box) — this is what turns Sentinel from a single
  snapshot into something that notices when attention on a topic is spiking
- **🔗 Entity Relationship Graph** — a simplified link-analysis graph showing
  which regions are connected through shared recent event categories
- **📡 Live Event Feed** — scrolling feed of the highest-severity tracked events
- **⬇ Export Intelligence Brief** *(new)* — one click downloads a plain-text
  summary of the current session: top risk regions, average severity, and
  whether the trend detector flagged an anomaly
- **🌓 Dark "ops-center" UI** — dashboard styled after real-world command-center
  interfaces
- **Resilient by design** — every data source (events, risk, trend) automatically
  falls back to realistic sample data if the live API is unavailable, so the
  dashboard always works for demos

## Tech Stack

| Layer          | Tool                                   |
|----------------|-----------------------------------------|
| UI / Dashboard | [Streamlit](https://streamlit.io/)      |
| Data Source    | [GDELT Project API](https://www.gdeltproject.org/) — Doc 2.0 (articles) and TimelineVolRaw (coverage volume), both free, no API key |
| Visualization  | Plotly (map + charts + network graph + trend line)   |
| Graph Analysis | NetworkX                                |
| Trend Fitting  | NumPy (linear regression via `polyfit`, z-score anomaly check) |
| Data Handling  | Pandas                                  |

## How It Works

1. **Data ingestion** — queries the GDELT Doc API for recent news articles
   matching keywords (e.g. "conflict OR cyberattack OR protest")
2. **Geolocation** — maps mentioned countries to coordinates for plotting
3. **Risk scoring** — each event type carries a weight (e.g. Conflict = 9,
   Diplomatic = 3); risk score per region = Σ(weight × severity/10),
   normalized to 0–100
4. **Trend + anomaly detection** — a second GDELT call (`mode=timelinevolraw`)
   returns daily coverage-volume counts for the same query over the last 14
   days. A simple linear fit (`numpy.polyfit`) extrapolates 2 days forward,
   and the most recent day is flagged anomalous if it's 1.5+ standard
   deviations from the mean of the preceding days
5. **Entity graph** — builds a graph where nodes are countries and edges
   connect countries that share a recent event category, using NetworkX +
   a spring layout for positioning
6. **Fallback mode** — if any API call fails or returns nothing, that module
   generates realistic sample data instead, so the dashboard never breaks a
   live demo

## Setup & Run

git clone <your-repo-url>
cd sentinel

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py


The app opens at `http://localhost:8501`. Click **🔄 Refresh live feed** in the
sidebar any time to force a fresh pull instead of waiting for the 5-minute
cache to expire.

## Project Structure

sentinel/
├── app.py               # Main Streamlit dashboard
├── data_source.py        # GDELT event fetching + risk score computation + fallback data
├── entity_graph.py       # Entity relationship graph construction (NetworkX)
├── trend_analysis.py     # Coverage-volume timeline, linear trend + anomaly detection
├── requirements.txt
└── README.md


## Possible Extensions

- Swap in NewsAPI or additional OSINT sources alongside GDELT
- Replace the linear trend with a proper time-series model (e.g. Holt-Winters
  via `statsmodels`) for a more robust forecast
- Add NLP-based entity extraction (spaCy NER) instead of keyword country matching
- Add user-defined "watchlists" for specific regions with per-region anomaly alerts
- Deploy on Streamlit Community Cloud for a live public demo link

## Disclaimer

All data used is publicly available open-source news data. This project does
not use, request, or simulate access to classified, private, or restricted
information of any kind. It is built purely for educational and portfolio
purposes to demonstrate data aggregation, visualization, and basic statistical
analysis techniques.
