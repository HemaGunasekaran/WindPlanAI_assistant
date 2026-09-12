# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NOTICE = 'Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.'
FEATURES = ["duration_hours", "wind_mean", "gust_max", "rain_max", "daylight_fraction"]


def generate(seed=42):
    """Entirely invented examples; no company or operational source data."""
    rng = np.random.default_rng(seed)
    times = pd.date_range("2026-06-15", periods=169, freq="h", tz="UTC")
    hour = times.hour.to_numpy()
    wind = np.clip(6 + 4 * np.sin(np.arange(len(times)) / 17) + rng.normal(0, 1, len(times)), 0, None)
    weather = pd.DataFrame({"time": times, "wind": wind.round(2),
        "gust": (wind + rng.uniform(1, 5, len(times))).round(2),
        "rain": np.where(rng.random(len(times)) < .18, rng.uniform(.2, 2, len(times)), 0).round(2),
        "is_day": ((hour >= 5) & (hour < 20)).astype(int)})
    n = 1600
    history = pd.DataFrame({"duration_hours": rng.integers(1, 9, n),
        "wind_mean": rng.uniform(0, 15, n), "gust_max": rng.uniform(5, 23, n),
        "rain_max": rng.uniform(0, 3, n), "daylight_fraction": rng.choice([0, .5, 1], n)})
    history["gust_max"] = np.maximum(history.gust_max, history.wind_mean + 1)
    logit = (2.8 - .14 * history.wind_mean - .09 * history.gust_max - .5 * history.rain_max
        - .16 * history.duration_hours + .65 * history.daylight_fraction
        + 1.7)
    history["completed_as_planned"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    history.insert(0, "activity", "Turbine installation")
    history.insert(0, "record_id", [f"DEMO-{i:04d}" for i in range(n)])
    weather["notice"] = NOTICE
    history["notice"] = NOTICE
    return weather, history


def load_demo():
    weather = pd.read_csv(ROOT / "data/demo_weather.csv")
    weather["time"] = pd.to_datetime(weather.time, utc=True)
    return weather


def load_history():
    return pd.read_csv(ROOT / "data/demo_history.csv")


def load_activities():
    return pd.read_csv(ROOT / "data/demo_activities.csv")
