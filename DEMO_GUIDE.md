# WindPlan AI demo guide

Generated demonstration records and illustrative limits; recommendations do not certify operational safety.

## Run and test

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

1. Open the Local URL printed by Streamlit. A new browser session starts without metrics or recommendations.
2. Select Offline demo and Turbine installation. Default values are 4 hours, wind 9 m/s, gust 13 m/s, precipitation 0.2 mm, daylight required.
3. Click **Find the safest time window**. Expect 17 valid windows in the fixed demo week.
4. Inspect recommendations and the Weather & validation tab. Select a window using **Select a window to explain**, below the top five cards. The selector includes all ranked windows.
5. **Explain Window**, next to the download button, enables only after selection. Clicking it calls OpenAI, if a key is configured. Merely searching, selecting, or downloading does not call OpenAI.
6. Change any sidebar scenario input. Previous results and explanations disappear. Click the search button to generate the new results.
7. **New scenario** clears results while retaining editable sidebar values. The results also start empty in a fresh browser session.
8. Select Live API and enter coordinates; click the search button. Forecast errors are displayed without restoring old results. A valid live forecast may have no suitable windows.

Results stay visible while selecting, explaining, or downloading so you can finish reviewing the current scenario. Search results are stored only in the current session. Weather retrieval uses a fresh request when you click search in live mode.

## Statistics

- **Valid windows:** candidate start times whose full activity interval passes every selected weather constraint. Windows may overlap, so this is not a count of independent jobs.
- **Starts checked:** hourly candidate starts evaluated, including those rejected for weather, darkness, missing observations, or insufficient forecast coverage at the end.
- **Activity duration:** the uninterrupted work time requested for each window. Four hours requires five hourly samples, checking both endpoints.

Example: 36 valid out of 152 checked means 116 candidate starts were rejected. Every accepted window provides the requested four-hour interval. It does not mean 36 turbines can be installed.

## OpenAI API key setup in VS Code

Do not paste the key into chat or app.py.

1. In this project's `.streamlit` folder, copy `secrets.toml.example` to a new file named `secrets.toml`.
2. Edit the local copy:

```toml
OPENAI_API_KEY = "your-actual-sk-key-here"
OPENAI_MODEL = "gpt-6-astra"
```

3. Save, stop Streamlit with Ctrl+C, and restart it. The secrets file is already excluded by `.gitignore`.
4. Generate windows, select one, and click **Explain Window**.

Alternatively, set OPENAI_API_KEY and optionally OPENAI_MODEL as server environment variables. The model is configurable to a Responses-compatible model available to your API project. The default follows the official quickstart example; availability depends on your project. If the call fails, check the key, model access, and API billing/quota. No additional Python package installation is needed: the adapter uses requests already in requirements.txt.

The key is sent only as the Authorization header to OpenAI. The request body contains selected weather facts, limits, dates, source mode, and a model score; it excludes coordinates and credentials. Requests set store=false. Clicking Explain Window can incur API usage charges. Explanations are stored in the current session only and cleared on a new search or scenario change. No paid call is made automatically.

Official setup reference: https://developers.openai.com/api/docs/quickstart

## AI roles

The local Random Forest ranks weather-valid windows using generated activity records. OpenAI then turns the chosen window's measured values and limits into a plain-language explanation. The LLM does not determine validity or modify rankings. The prompt requires it to explain constraint headroom, duration, daylight, and sampling limitations without asserting that the operation is certified safe. No real-world cost, safety, or completion improvement has been established from demo data.

## Automated checks

```bash
python -m unittest discover -s tests -v
```

The suite tests the empty initial screen, explicit searches, clearing on edits/reset, window selection, explanation request gating, error handling, and the weather-validation engine. OpenAI responses are mocked for tests; a real OpenAI call requires your locally configured API key.
