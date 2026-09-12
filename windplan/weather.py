# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
import numpy as np
import pandas as pd
import requests

API_URL = "https://api.open-meteo.com/v1/forecast"


def validate_weather(frame):
    required = ["time", "wind", "gust", "rain", "is_day"]
    if not set(required).issubset(frame.columns) or frame.empty:
        raise ValueError("Weather is empty or missing required columns.")
    result = frame[required].copy()
    result["time"] = pd.to_datetime(result.time, utc=True, errors="raise")
    if result.time.isna().any() or result.time.duplicated().any():
        raise ValueError("Weather timestamps must be present and unique.")
    for col in required[1:]:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    # Missing/nonfinite observations remain unavailable and fail window validation.
    invalid = (~np.isfinite(result[required[1:]]).all(axis=1)
        | (result[["wind", "gust", "rain"]] < 0).any(axis=1)
        | ~result.is_day.isin([0, 1]) | (result.gust < result.wind))
    result.loc[invalid, required[1:]] = np.nan
    return result.sort_values("time").reset_index(drop=True)


def fetch_weather(latitude, longitude):
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Coordinates are outside valid ranges.")
    response = requests.get(API_URL, params={"latitude": latitude, "longitude": longitude,
        "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,is_day",
        "wind_speed_unit": "ms", "precipitation_unit": "mm", "timezone": "UTC",
        "forecast_days": 7}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    try:
        units = payload["hourly_units"]
        if any(units[k] != v for k, v in {"wind_speed_10m": "m/s", "wind_gusts_10m": "m/s", "precipitation": "mm"}.items()):
            raise ValueError("Unexpected weather units.")
        h = payload["hourly"]
        frame = pd.DataFrame({"time": h["time"], "wind": h["wind_speed_10m"],
            "gust": h["wind_gusts_10m"], "rain": h["precipitation"], "is_day": h["is_day"]})
        return validate_weather(frame)
    except (KeyError, TypeError) as exc:
        raise ValueError("Weather provider returned an unexpected response.") from exc
