"""
trend_analysis.py
Adds a temporal dimension to Sentinel: pulls a daily coverage-volume
timeline for the active search query from GDELT's TimelineVolRaw mode,
fits a simple linear trend, projects a short forecast, and flags days
that deviate sharply from the recent baseline using a z-score check.

This is what turns Sentinel from a one-time snapshot into something that
tracks whether attention on a topic is accelerating, flat, or spiking.
"""

import requests
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_volume_timeline(query, timespan="14days"):
    """
    Pulls a daily article-volume timeline matching the query from GDELT.
    Falls back to a realistic synthetic timeline if the live call fails,
    exactly like the rest of Sentinel's data sources.

    Returns: (DataFrame[date, value], mode) where mode is "live" or "sample"
    """
    try:
        params = {"query": query, "mode": "timelinevolraw", "format": "json", "timespan": timespan}
        resp = requests.get(GDELT_URL, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        series = data.get("timeline", [])
        if not series:
            raise ValueError("empty timeline response")

        points = series[0].get("data", [])
        rows = []
        for p in points:
            dt = _parse_date(p.get("date", ""))
            if dt is not None:
                rows.append({"date": dt, "value": p.get("value", 0)})

        if len(rows) < 4:
            raise ValueError("insufficient data points returned")

        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return df, "live"

    except Exception:
        return _sample_timeline(), "sample"


def _parse_date(raw):
    """GDELT has returned dates in a couple of different formats over time; try each."""
    for fmt in ("%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def _sample_timeline(days=14):
    """Synthetic 14-day coverage volume with a mild upward drift and a spike near
    the end, so the anomaly detector always has something realistic to catch
    when running offline."""
    now = datetime.utcnow()
    base = 42
    rows = []
    for i in range(days):
        d = now - timedelta(days=(days - 1 - i))
        val = max(5, base + random.uniform(-9, 9) + i * 0.6)
        rows.append({"date": d, "value": round(val, 1)})
    rows[-1]["value"] = round(rows[-1]["value"] * 1.75, 1)
    return pd.DataFrame(rows)


def analyze(df):
    """
    Fits a linear trend over the timeline, projects 2 days forward, and
    flags the most recent point as anomalous if it sits 1.5+ standard
    deviations from the mean of everything before it.
    """
    d = df.copy().reset_index(drop=True)
    y = d["value"].to_numpy(dtype=float)
    x = np.arange(len(y))

    if len(y) < 4:
        return {"has_forecast": False, "anomaly": False, "z_score": 0.0}

    slope, intercept = np.polyfit(x, y, 1)
    future_x = np.array([len(y), len(y) + 1])
    future_y = slope * future_x + intercept

    baseline = y[:-1]
    mean, std = baseline.mean(), (baseline.std() or 1.0)
    z = (y[-1] - mean) / std
    anomaly = abs(z) >= 1.5

    return {
        "has_forecast": True,
        "forecast_x": future_x,
        "forecast_y": future_y,
        "slope": float(slope),
        "anomaly": bool(anomaly),
        "z_score": round(float(z), 2),
    }
