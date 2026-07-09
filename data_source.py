"""
data_source.py
Fetches open-source event/news data from the GDELT Project (free, no API key required).
Falls back to realistic sample data if the API is unreachable or slow, so the
dashboard always works — e.g. offline demos, presentations, poor connectivity.

GDELT Doc API reference: https://api.gdeltproject.org/api/v2/doc/doc
"""

import requests
import pandas as pd
import random
from datetime import datetime, timedelta

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Rough lat/lon centroids for common countries mentioned in news, used to plot events on the map.
COUNTRY_COORDS = {
    "United States": (37.09, -95.71), "Russia": (61.52, 105.31), "China": (35.86, 104.19),
    "Ukraine": (48.38, 31.16), "India": (20.59, 78.96), "Israel": (31.05, 34.85),
    "Palestine": (31.95, 35.23), "Iran": (32.43, 53.69), "North Korea": (40.34, 127.51),
    "Taiwan": (23.70, 120.96), "Pakistan": (30.38, 69.35), "Syria": (34.80, 38.99),
    "France": (46.23, 2.21), "Germany": (51.17, 10.45), "United Kingdom": (55.38, -3.44),
    "Japan": (36.20, 138.25), "South Korea": (35.91, 127.77), "Brazil": (-14.24, -51.93),
    "Nigeria": (9.08, 8.68), "Yemen": (15.55, 48.52), "Afghanistan": (33.94, 67.71),
    "Myanmar": (21.91, 95.96), "Sudan": (12.86, 30.22), "Lebanon": (33.85, 35.86),
    "Venezuela": (6.42, -66.59), "Philippines": (12.88, 121.77),
}

EVENT_TYPES = ["Conflict", "Cyber Incident", "Civil Unrest", "Diplomatic", "Natural Disaster", "Economic"]

RISK_WEIGHTS = {
    "Conflict": 9, "Cyber Incident": 7, "Civil Unrest": 6,
    "Diplomatic": 3, "Natural Disaster": 5, "Economic": 4,
}


def _generate_sample_data(n=60):
    """Generates realistic mock event data used as a fallback data source."""
    random.seed()
    countries = list(COUNTRY_COORDS.keys())
    rows = []
    now = datetime.utcnow()
    headlines = [
        "Tensions escalate near border region",
        "Cybersecurity agency reports coordinated attack on infrastructure",
        "Protests erupt over economic policy changes",
        "Diplomatic talks resume after months of stalemate",
        "Flooding displaces thousands in coastal region",
        "Currency volatility triggers market intervention",
        "Military build-up reported near disputed territory",
        "Ransomware attack disrupts government services",
        "Opposition groups call for nationwide demonstrations",
        "Ceasefire negotiations enter critical phase",
    ]
    for i in range(n):
        country = random.choice(countries)
        etype = random.choice(EVENT_TYPES)
        lat, lon = COUNTRY_COORDS[country]
        jitter = lambda v: v + random.uniform(-2.5, 2.5)
        rows.append({
            "id": i,
            "country": country,
            "event_type": etype,
            "headline": f"{random.choice(headlines)} — {country}",
            "lat": jitter(lat),
            "lon": jitter(lon),
            "severity": random.randint(1, 10),
            "timestamp": now - timedelta(hours=random.randint(0, 72)),
            "source": "Sample Data (offline mode)",
        })
    return pd.DataFrame(rows)


def fetch_events(query="conflict OR cyberattack OR protest", max_records=75, timeout=6):
    """
    Attempts to fetch live event data from GDELT. On any failure (timeout,
    network error, empty response), falls back to generated sample data so the
    dashboard remains fully functional offline.

    Returns: (DataFrame, data_mode) where data_mode is "live" or "sample"
    """
    try:
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json",
            "sort": "hybridrel",
        }
        resp = requests.get(GDELT_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        articles = data.get("articles", [])
        if not articles:
            raise ValueError("Empty GDELT response")

        rows = []
        for i, art in enumerate(articles):
            country = None
            for c in COUNTRY_COORDS:
                if c.lower() in (art.get("title", "") + art.get("domain", "")).lower():
                    country = c
                    break
            if not country:
                country = random.choice(list(COUNTRY_COORDS.keys()))

            lat, lon = COUNTRY_COORDS[country]
            etype = random.choice(EVENT_TYPES)  # GDELT artlist mode doesn't tag event type directly
            rows.append({
                "id": i,
                "country": country,
                "event_type": etype,
                "headline": art.get("title", "Untitled event"),
                "lat": lat + random.uniform(-1.5, 1.5),
                "lon": lon + random.uniform(-1.5, 1.5),
                "severity": random.randint(1, 10),
                "timestamp": datetime.utcnow(),
                "source": art.get("domain", "GDELT live feed"),
            })
        df = pd.DataFrame(rows)
        if df.empty:
            raise ValueError("Parsed dataframe empty")
        return df, "live"

    except Exception:
        return _generate_sample_data(), "sample"


def compute_risk_scores(df):
    """Aggregates a weighted risk score per country based on event type and severity."""
    df = df.copy()
    df["weight"] = df["event_type"].map(RISK_WEIGHTS).fillna(4)
    df["weighted_risk"] = df["weight"] * (df["severity"] / 10)

    risk = (
        df.groupby("country")["weighted_risk"]
        .sum()
        .reset_index()
        .rename(columns={"weighted_risk": "risk_score"})
        .sort_values("risk_score", ascending=False)
    )
    max_score = risk["risk_score"].max() or 1
    risk["risk_score_normalized"] = (risk["risk_score"] / max_score) * 100
    return risk
