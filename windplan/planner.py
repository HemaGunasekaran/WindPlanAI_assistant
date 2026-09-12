# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
from dataclasses import dataclass
import numpy as np
import pandas as pd
from windplan.data import FEATURES
from windplan.weather import validate_weather


@dataclass(frozen=True)
class Constraints:
    duration_hours: int = 4
    wind: float = 10
    gust: float = 15
    rain: float = 1
    daylight: bool = True

    def __post_init__(self):
        if not isinstance(self.duration_hours, int) or not 1 <= self.duration_hours <= 24:
            raise ValueError("Duration must be an integer from 1 to 24 hours.")
        if any(not np.isfinite(v) or v < 0 for v in (self.wind, self.gust, self.rain)):
            raise ValueError("Limits must be finite and nonnegative.")


def rank_windows(weather, limits, model, earliest=None):
    """Check duration+1 hourly samples, including the finishing boundary.

    Precipitation is a preceding-hour accumulation. Checking both boundaries
    conservatively includes one extra accumulation at the start.
    """
    weather = validate_weather(weather)
    earliest = pd.Timestamp(earliest) if earliest is not None else weather.time.min()
    earliest = earliest.tz_localize("UTC") if earliest.tzinfo is None else earliest.tz_convert("UTC")
    indexed = weather.set_index("time")
    rows = []
    for start in weather.time[weather.time >= earliest]:
        times = pd.date_range(start, periods=limits.duration_hours + 1, freq="h")
        segment = indexed.reindex(times)
        reasons = []
        if segment.isna().any().any():
            reasons.append("Missing weather or incomplete hourly coverage")
        else:
            for field, label in [("wind", "Wind"), ("gust", "Gust"), ("rain", "Rain")]:
                if segment[field].max() > getattr(limits, field):
                    reasons.append(f"{label} exceeds {getattr(limits, field):g}")
            if limits.daylight and not segment.is_day.eq(1).all():
                reasons.append("Daylight does not cover the full window")
        rows.append({"start": start, "end": times[-1], "valid": not reasons,
            "wind_max": segment.wind.max(), "gust_max": segment.gust.max(), "rain_max": segment.rain.max(),
            "wind_mean": segment.wind.mean(), "daylight_fraction": segment.is_day.mean(),
            "explanation": "; ".join(reasons)})
    audit = pd.DataFrame(rows)
    if audit.empty:
        return pd.DataFrame(), audit
    valid = audit[audit.valid].copy()
    if valid.empty:
        return valid, audit
    features = valid.assign(duration_hours=limits.duration_hours)[FEATURES]
    valid["context_score"] = model.predict_proba(features)[:, list(model.classes_).index(1)] * 100
    valid["explanation"] = valid.apply(lambda r: (
        f"All {limits.duration_hours} hours plus the end boundary pass. "
        f"Peak wind {r.wind_max:.1f}/{limits.wind:g} m/s; gust {r.gust_max:.1f}/{limits.gust:g} m/s; "
        f"precipitation {r.rain_max:.1f}/{limits.rain:g} mm. "
        f"Daylight {'required and satisfied' if limits.daylight else 'not required'}. "
        f"Historical-context score {r.context_score:.1f}/100."), axis=1)
    return valid.sort_values(["context_score", "start"], ascending=[False, True]).reset_index(drop=True), audit
