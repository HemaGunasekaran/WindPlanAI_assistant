# WindPlan AI

> Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.

An independent Streamlit hackathon prototype that finds uninterrupted weather windows for fictional wind-installation activities and ranks valid options using a Random Forest historical-context model.

All activity records, outcomes, default thresholds, and offline weather are generated from scratch. No company datasets, costs, names, requirements, or proprietary constraints are included. The earlier concept was not available in this empty workspace; this implementation follows the requested feature list.

## Quick start

Use Python 3.11 or 3.12 (recommended).

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open http://localhost:8501. The app starts in **Offline demo** mode. Once dependencies are installed, this mode needs no network, account, API key, or model download. Paths to bundled data work independently of the current working directory.

## Two weather modes

- **Live API:** enter latitude and longitude to fetch seven days of hourly Open-Meteo forecast data. All times are UTC. Only future whole-hour starts are considered. Each submitted live search refreshes weather, on explicit search. Errors are displayed explicitly; select offline mode to continue if the service is unavailable.

Live data uses wind speed and gust at **10 m** in m/s, total hourly precipitation in mm (rain, showers, and snow), and the provider's daylight flag. API requests have a 20-second timeout and validate units. See the [Open-Meteo forecast documentation](https://open-meteo.com/en/docs), [terms](https://open-meteo.com/en/terms), and [weather attribution/license](https://open-meteo.com/en/licence). The public endpoint is intended here for a non-commercial hackathon; check service terms for other uses. Forecast attribution: Open-Meteo, CC BY 4.0.

## Validation and ranking

2. For each candidate start, require every hourly sample from start through end, including both endpoints. A four-hour activity checks five timestamps. No combining disconnected good hours or accepting a favorable average over a bad hour.
3. Reject windows with any missing/invalid observation, a gap, an exceeded ceiling, or darkness when daylight is required. Equality with a ceiling is accepted. Duplicate timestamps reject the input; unordered data is sorted.
4. Rank only valid windows by the model's demo context score; break ties by earliest start. Show peak conditions against limits, daylight status, duration, and the score. Rejected starts and reasons are visible in the audit table. Download all valid windows as CSV.

This is continuous coverage **at hourly resolution**, not a continuous-time guarantee. Wind is sampled; gust and precipitation reflect preceding-hour values. Both endpoints are checked conservatively, including one extra precipitation accumulation at the start. Requiring daylight at both endpoints also conservatively rejects windows finishing at a night sample. Changes between samples are unknown. Missing horizon-end coverage is rejected. Windows can overlap; the app does not assign crews or sequence multiple activities.

## Historical-context model

`RandomForestClassifier` uses duration, mean wind, peak gust, peak precipitation, daylight fraction. It learns `completed_as_planned` from 1,600 seeded demo records. Labels are sampled from a documented logistic formula in `windplan/data.py`; no external data is involved. The activity label and record ID are excluded from features. The 75/25 stratified split yields 1,200 training records and 400 held-out records. Training is cached in memory and deterministic (seed 42).

The model tab exposes holdout accuracy, ROC AUC, and global feature importance. These metrics measure only the invented distribution. Scores are uncalibrated model outputs, not real-world completion probabilities. Per-window explanations report measured constraints and model inputs; global feature importance is not a causal or local attribution. The model cannot override the weather gate. Inputs outside the demo training ranges may produce unreliable rankings.

## Demo walkthrough (about 3 minutes)

1. Launch with the default offline mode. Show the valid-window count and top five recommendations.
2. Open **Weather & validation** to compare wind/gust curves, precipitation, and rejection reasons.
3. Reduce maximum wind to zero: show the no-valid-window state. Restore it to 10 m/s.
4. Increase duration or toggle the daylight requirement and show how the eligible windows change.
5. Review the top five ranked windows; use the selector or download to access all valid windows.
6. Open **Model & demo data** to show the held-out metrics and fictional training rows.
7. Download ranked windows. Switch to **Live API**, enter coordinates, and show forecast charts and future starts. If the service is unreachable, demonstrate the explicit error and return to offline mode.

These instructions are the included demo alternative to screenshots.

## Tests and regeneration

```bash
python -m unittest discover -s tests -v
python -m scripts.generate_data
```

Tests cover full-duration/end-boundary checks, every weather constraint, threshold equality, missing/nonfinite data, timestamp gaps and duplicates, sorting, future starts, score ordering, reproducible generation, mocked API units/timeouts/errors, and a Streamlit offline UI smoke test. No live internet call is required by the test suite.

## Repository

```text
app.py                       Streamlit UI, caching, live/offline controls
windplan/data.py             Demo generator and file loaders
windplan/weather.py          Open-Meteo adapter and weather validation
windplan/model.py            Random Forest training and holdout metrics
windplan/planner.py          Hard constraints, full-window checks, ranking
scripts/generate_data.py     Seeded CSV regeneration
data/                       Demo activities, history, and weather CSV files
tests/                      Standard-library unittest suite + AppTest
requirements.txt             Runtime and UI-test dependencies
.streamlit/config.toml       App theme
```

## Scope

A hackathon planning demonstration, not an operational lift planner. It does not model hub-height wind, crane configuration, local terrain, forecast uncertainty, equipment certification, staffing conflicts, or actual safety procedures. No costs or company requirements are modeled. Any real deployment needs independently supplied and validated operational inputs and forecast handling.


## Final demo version


## Current interaction and optional LLM

The app starts empty and searches only when you click **Find the safest time window**. Changing sidebar inputs or clicking **New scenario** clears results. Only **Turbine installation** is offered. After a search, select any ranked window to enable **Explain Window** beside the CSV download. OpenAI explanations are optional; local ranking and weather search do not need an OpenAI key. See [DEMO_GUIDE.md](DEMO_GUIDE.md) for the current acceptance test, metric definitions, and local key setup. The OpenAI integration uses the Responses REST API via requests; no new dependency is needed.
