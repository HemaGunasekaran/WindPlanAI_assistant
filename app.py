# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
import os
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
from windplan.data import NOTICE, load_activities, load_demo, load_history
from windplan.model import train_model
from windplan.planner import Constraints, rank_windows
from windplan.weather import fetch_weather
from windplan.explanations import explain_window

ASSETS = Path(__file__).resolve().parent / "assets"
st.set_page_config(page_title="WindPlan AI", page_icon=str(ASSETS / "turbine.svg"), layout="wide")
st.markdown("""<style>
.stApp {background:#f5f8fc;color:#0b2545;color-scheme:light;}
[data-testid="stHeader"] {background:#f5f8fc;}
[data-testid="stSidebar"] {background:#0b2545;}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] label p, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#fff !important;}
[data-testid="stMetric"] {background:white;border:1px solid #dce6f2;border-radius:14px;padding:18px;}
h1,h2,h3 {color:#0b2545;}
.stButton button[kind="primary"] {background:#2563eb;color:white;border:0;}
</style>""", unsafe_allow_html=True)
logo, heading = st.columns([1, 10])
with logo:
    st.image(str(ASSETS / "turbine.svg"), width=76)
with heading:
    st.title("WindPlan AI")
    st.write("From weather forecast to explainable time windows.")

@st.cache_resource
def get_model(history):
    return train_model(history)

@st.cache_data(ttl=900, show_spinner=False)
def get_live(lat, lon):
    return fetch_weather(lat, lon), pd.Timestamp.now(tz="UTC")

with st.sidebar:
    st.header("Plan a window")
    mode = st.radio("Weather source", ["Offline demo", "Live API"])
    activities = load_activities().set_index("activity")
    activity = st.selectbox("What are you planning?", ["Turbine installation"])
    preset = activities.loc[activity]
    st.caption("Illustrative presets; you can adjust each limit below.")
    duration = st.slider("Duration (hours)", 1, 12, int(preset.duration_hours), key=f"duration_{activity}")
    wind = st.number_input("Maximum wind (m/s)", 0., 40., float(preset.wind), .5, key=f"wind_{activity}")
    gust = st.number_input("Maximum gust (m/s)", 0., 60., float(preset.gust), .5, key=f"gust_{activity}")
    rain = st.number_input("Maximum hourly precipitation (mm)", 0., 20., float(preset.rain), .1, key=f"rain_{activity}")
    daylight = st.checkbox("Require daylight for entire window", bool(preset.daylight), key=f"daylight_{activity}")
    if mode == "Live API":
        lat = st.number_input("Latitude", -90., 90., 54., .01)
        lon = st.number_input("Longitude", -180., 180., 8., .01)
    search = st.button("Find the safest time window", type="primary", width="stretch")
    reset = st.button("New scenario", width="stretch")

scenario = (mode, activity, duration, wind, gust, rain, daylight,
            lat if mode == "Live API" else None, lon if mode == "Live API" else None)
if reset or st.session_state.get("scenario") != scenario or search:
    for key in ("results", "selected_window", "llm_explanation"):
        st.session_state.pop(key, None)
    st.session_state["scenario"] = scenario
if not search and "results" not in st.session_state:
    st.caption("Set your inputs in the sidebar, then click Find the safest time window.")
    st.stop()


if search:
    if mode == "Live API":
        get_live.clear()
        try:
            with st.spinner("Loading forecast…"):
                weather, retrieved = get_live(lat, lon)
            earliest = pd.Timestamp.now(tz="UTC").ceil("h")
            st.caption("Weather: [Open-Meteo](https://open-meteo.com/) • [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)")
        except (requests.RequestException, ValueError) as exc:
            st.error(f"Live forecast unavailable: {exc}")
            st.info("Select Offline demo in the sidebar to continue without a network connection.")
            st.stop()
    else:
        weather = load_demo()
        earliest = weather.time.min()
        st.caption("Offline demo • 15–22 June 2026 • All times UTC")
    
    model, metrics = get_model(load_history())
    limits = Constraints(duration, wind, gust, rain, daylight)
    ranked, audit = rank_windows(weather, limits, model, earliest=earliest)
    st.session_state["results"] = (weather, retrieved if mode == "Live API" else None, model, metrics, limits, ranked, audit)
weather, retrieved, model, metrics, limits, ranked, audit = st.session_state["results"]
a, b, c = st.columns(3)
a.metric("Valid windows", len(ranked), help="Candidate start times whose entire activity interval passes all selected limits. Windows can overlap.")
b.metric("Starts checked", len(audit), help="Hourly candidate start times assessed, including rejected starts and those with incomplete end coverage.")
c.metric("Activity duration", f"{duration} hours", help="Required uninterrupted work time for every candidate window.")
recommendations, forecast, diagnostics = st.tabs(["Recommended windows", "Weather & validation", "Model & demo data"])
with recommendations:
    st.subheader(activity)
    st.caption("Ranked by Random Forest historical-context score, then earliest start. Scores are uncalibrated demo-model outputs, not real-world success probabilities. Windows may overlap; this is not a multi-activity schedule.")
    if ranked.empty:
        st.warning("No complete window meets these constraints. Inspect rejection reasons or adjust the demo inputs.")
    else:
        st.caption(f"Showing the top {min(5, len(ranked))} of {len(ranked)} ranked windows. All valid windows are available in the selector and CSV download below.")
        for i, row in ranked.head(5).iterrows():
            with st.container(border=True):
                st.markdown(f"### {i + 1}. {row.start:%a %d %b, %H:%M} → {row.end:%d %b, %H:%M} UTC")
                st.write(row.explanation)
        selected = st.selectbox("Select a window to explain", options=ranked.index.tolist(), index=None,
            placeholder="Choose a ranked window", key="selected_window",
            format_func=lambda i: f"{i+1}. {ranked.iloc[i].start:%d %b %H:%M} → {ranked.iloc[i].end:%d %b %H:%M} UTC")
        download_col, explain_col = st.columns(2)
        with download_col:
            st.download_button("Download all ranked windows", ranked.assign(activity=activity, weather_source=mode, latitude=lat if mode == "Live API" else None, longitude=lon if mode == "Live API" else None, weather_retrieved_utc=str(retrieved) if mode == "Live API" else "fixed demo week", duration_hours=duration, wind_limit=wind, gust_limit=gust, rain_limit=rain, daylight_required=daylight, notice=NOTICE).to_csv(index=False), "windplan_windows.csv", "text/csv")
        with explain_col:
            explain_clicked = st.button("Explain Window", disabled=selected is None, width="stretch")
        st.caption("Explain Window sends the selected window’s weather values and limits to OpenAI. API usage may incur charges. Coordinates and your key are not included in the explanation text.")
        if explain_clicked and selected is not None:
            row = ranked.iloc[selected]
            api_key = os.environ.get("OPENAI_API_KEY", "")
            llm_model = os.environ.get("OPENAI_MODEL", "gpt-6-astra")
            try:
                api_key = api_key or st.secrets.get("OPENAI_API_KEY", "")
                llm_model = st.secrets.get("OPENAI_MODEL", llm_model)
            except FileNotFoundError:
                pass
            facts = {"activity": activity, "weather_source": mode, "start_utc": str(row.start),
                "end_utc": str(row.end), "duration_hours": duration, "samples_checked": duration + 1,
                "peak_wind_ms": float(row.wind_max), "wind_limit_ms": wind,
                "peak_gust_ms": float(row.gust_max), "gust_limit_ms": gust,
                "peak_precipitation_mm": float(row.rain_max), "precipitation_limit_mm": rain,
                "daylight_required": daylight, "daylight_fraction": float(row.daylight_fraction),
                "all_samples_pass": True, "demo_model_context_score": float(row.context_score)}
            st.session_state.pop("llm_explanation", None)
            try:
                with st.spinner("Explaining the selected window…"):
                    explanation = explain_window(facts, api_key, llm_model)
                st.session_state["llm_explanation"] = (selected, explanation)
            except ValueError as exc:
                st.error(str(exc))
        saved = st.session_state.get("llm_explanation")
        if saved and saved[0] == selected:
            st.subheader("Window explanation")
            st.write(saved[1])

with forecast:
    st.subheader("Wind and gust forecast (m/s)")
    st.line_chart(weather.set_index("time")[["wind", "gust"]], color=["#2563eb", "#0b2545"])
    st.subheader("Hourly precipitation (mm)")
    st.bar_chart(weather.set_index("time")[["rain"]])
    st.caption("Validation checks every hourly sample from start through finish, including both boundaries. Precipitation is the preceding-hour total; the start sample is included conservatively. Night at either boundary rejects daylight-only work. Missing samples fail closed.")
    st.dataframe(audit, hide_index=True, width="stretch")
with diagnostics:
    st.caption("Generated demonstration records and illustrative limits. Recommendations support review and do not certify operational safety. Weather is sampled hourly at 10 m; conditions between samples and at equipment height may differ.")
    st.write("Random Forest classifier trained on 1,200 fictional activities, evaluated on 400 separate fictional records. Labels are probabilistically generated; metrics only describe this invented distribution.")
    st.write("The model is compared with a baseline that always predicts the training-set completion rate. Lower Brier loss means better probability predictions on the demo holdout. This does not establish real-world benefit.")
    st.json(metrics)
    st.bar_chart(pd.Series(model.feature_importances_, index=model.feature_names_in_, name="Global feature importance"))
    st.caption("Feature importance is a global model diagnostic, not a causal or per-window explanation. Activity labels are excluded from model features.")
    st.dataframe(load_history().head(30), hide_index=True)
