# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
"""Run from repository root: python -m scripts.generate_data."""
from windplan.data import ROOT, generate

if __name__ == "__main__":
    weather, history = generate()
    (ROOT / "data").mkdir(exist_ok=True)
    weather.to_csv(ROOT / "data/demo_weather.csv", index=False)
    history.to_csv(ROOT / "data/demo_history.csv", index=False, float_format="%.5f")
    print(f"Generated {len(weather)} hourly samples and {len(history)} demo activities.")
