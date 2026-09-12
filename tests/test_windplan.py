# Generated demonstration data. Limits are illustrative and must not be used for real lifting operations.
import unittest
from unittest.mock import patch, Mock
import numpy as np
import pandas as pd
import requests
from windplan.data import generate, load_demo, load_history
from windplan.model import train_model
from windplan.planner import Constraints, rank_windows
from windplan.weather import fetch_weather, validate_weather


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.metrics = train_model(load_history())

    def setUp(self):
        self.weather = pd.DataFrame({"time": pd.date_range("2026-06-15T08:00Z", periods=7, freq="h"),
            "wind": 5., "gust": 8., "rain": 0., "is_day": 1})

    def rank(self, weather=None, limits=None, **kwargs):
        return rank_windows(self.weather if weather is None else weather, limits or Constraints(), self.model, **kwargs)

    def test_full_duration_and_boundary(self):
        ranked, audit = self.rank()
        self.assertEqual(len(ranked), 3)
        self.assertEqual(len(audit), 7)
        self.weather.loc[4, "gust"] = 20
        self.assertTrue(self.rank()[0].empty)

    def test_each_constraint_rejects(self):
        for field, value in [("wind", 11), ("gust", 16), ("rain", 1.1), ("is_day", 0)]:
            with self.subTest(field=field):
                frame = self.weather.copy()
                frame.loc[3, field] = value
                self.assertTrue(self.rank(frame)[0].empty)

    def test_missing_gap_and_nonfinite_fail_closed(self):
        self.assertTrue(self.rank(self.weather.drop(index=3))[0].empty)
        for value in [np.nan, np.inf, -1]:
            frame = self.weather.copy()
            frame.loc[3, "rain"] = value
            self.assertTrue(self.rank(frame)[0].empty)

    def test_threshold_equality_and_optional_daylight(self):
        self.weather["wind"], self.weather["gust"], self.weather["rain"] = 10, 15, 1
        self.weather["is_day"] = 0
        self.assertEqual(len(self.rank(limits=Constraints(daylight=False))[0]), 3)

    def test_duplicates_rejected_and_order_normalized(self):
        with self.assertRaises(ValueError):
            self.rank(pd.concat([self.weather, self.weather.iloc[:1]]))
        self.assertEqual(len(self.rank(self.weather.iloc[::-1])[0]), 3)

    def test_no_past_starts_and_ranking(self):
        ranked, _ = self.rank(earliest="2026-06-15T09:00Z")
        self.assertEqual(len(ranked), 2)
        self.assertTrue(ranked.context_score.is_monotonic_decreasing)
        self.assertTrue(ranked.context_score.between(0, 100).all())
        self.assertTrue(ranked.explanation.str.contains("pass").all())

    def test_demo_end_to_end(self):
        ranked, _ = self.rank(load_demo())
        self.assertGreater(len(ranked), 0)
        self.assertEqual(self.metrics["test_rows"], 400)
        a, b = generate()
        c, d = generate()
        pd.testing.assert_frame_equal(a, c)
        pd.testing.assert_frame_equal(b, d)

    def test_ai_cannot_change_eligibility(self):
        first, audit = self.rank()
        second = audit[audit.valid]
        self.assertEqual(set(first.start), set(second.start))
        self.assertIn("baseline_brier_loss", self.metrics)

    def test_invalid_limits(self):
        for kwargs in [{"duration_hours": 0}, {"duration_hours": 1.5}, {"wind": -1}, {"rain": np.inf}]:
            with self.assertRaises(ValueError):
                Constraints(**kwargs)


class WeatherTests(unittest.TestCase):
    def payload(self):
        return {"hourly_units": {"wind_speed_10m": "m/s", "wind_gusts_10m": "m/s", "precipitation": "mm"},
            "hourly": {"time": ["2026-06-15T08:00"], "wind_speed_10m": [5],
                "wind_gusts_10m": [8], "precipitation": [0], "is_day": [1]}}

    @patch("windplan.weather.requests.get")
    def test_api_contract(self, get):
        get.return_value = Mock(json=Mock(return_value=self.payload()))
        weather = fetch_weather(54, 8)
        self.assertEqual(weather.wind.iloc[0], 5)
        self.assertEqual(str(weather.time.dt.tz), "UTC")
        self.assertEqual(get.call_args.kwargs["params"]["wind_speed_unit"], "ms")
        self.assertEqual(get.call_args.kwargs["timeout"], 20)

    @patch("windplan.weather.requests.get")
    def test_errors_and_bad_units(self, get):
        get.side_effect = requests.Timeout("timeout")
        with self.assertRaises(requests.Timeout):
            fetch_weather(54, 8)
        get.side_effect = None
        payload = self.payload()
        payload["hourly_units"]["wind_speed_10m"] = "km/h"
        get.return_value = Mock(json=Mock(return_value=payload))
        with self.assertRaises(ValueError):
            fetch_weather(54, 8)

    @patch("windplan.weather.requests.get")
    def test_malformed_and_http_failure(self, get):
        get.return_value = Mock(json=Mock(return_value={}))
        with self.assertRaises(ValueError):
            fetch_weather(54, 8)
        get.return_value.raise_for_status.side_effect = requests.HTTPError("503")
        with self.assertRaises(requests.HTTPError):
            fetch_weather(54, 8)

    def test_bad_coordinates(self):
        with self.assertRaises(ValueError):
            fetch_weather(100, 8)


class AppTests(unittest.TestCase):
    def test_start_search_change_reset(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file("app.py").run(timeout=30)
        self.assertEqual(len(app.metric), 0)
        self.assertEqual(app.sidebar.selectbox[0].options, ["Turbine installation"])
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(int(app.metric[0].value), 17)
        self.assertTrue(next(b for b in app.button if b.label == "Explain Window").disabled)
        app.selectbox(key="selected_window").set_value(0).run()
        self.assertFalse(next(b for b in app.button if b.label == "Explain Window").disabled)
        self.assertEqual(int(app.metric[0].value), 17)
        app.sidebar.number_input[0].set_value(8).run()
        self.assertEqual(len(app.metric), 0)
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        app.sidebar.button[1].click().run()
        self.assertEqual(len(app.metric), 0)
        fresh = AppTest.from_file("app.py").run()
        self.assertEqual(len(fresh.metric), 0)

    @patch("windplan.explanations.explain_window", return_value="The selected window meets the supplied wind limit.")
    def test_selected_explanation(self, explain):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file("app.py").run(timeout=30)
        app.sidebar.button[0].click().run()
        self.assertFalse(explain.called)
        app.selectbox(key="selected_window").set_value(0).run()
        next(b for b in app.button if b.label == "Explain Window").click().run()
        self.assertEqual(len(app.exception), 0)
        explain.assert_called_once()
        self.assertTrue(explain.call_args.args[0]["all_samples_pass"])
        self.assertNotIn("latitude", explain.call_args.args[0])
        app.selectbox(key="selected_window").set_value(1).run()
        self.assertFalse(any(m.value == explain.return_value for m in app.markdown))

    @patch("windplan.weather.requests.get")
    def test_live_failure_recovery(self, get):
        from streamlit.testing.v1 import AppTest
        get.side_effect = requests.Timeout("outage")
        app = AppTest.from_file("app.py").run(timeout=30)
        app.sidebar.radio[0].set_value("Live API").run()
        self.assertFalse(get.called)
        app.sidebar.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Live forecast unavailable", app.error[0].value)
        app.sidebar.radio[0].set_value("Offline demo").run()
        self.assertEqual(len(app.metric), 0)
        app.sidebar.button[0].click().run()
        self.assertEqual(int(app.metric[0].value), 17)


class ExplanationTests(unittest.TestCase):
    @patch("windplan.explanations.requests.post")
    def test_request_and_errors(self, post):
        from windplan.explanations import explain_window
        with self.assertRaises(ValueError):
            explain_window({}, "")
        self.assertFalse(post.called)
        post.return_value = Mock(status_code=200, json=Mock(return_value={"status":"completed", "output":[
            {"type":"message", "content":[{"type":"output_text", "text":"Meets the selected limits."}]}]}))
        self.assertEqual(explain_window({"wind":5}, "test-key"), "Meets the selected limits.")
        body = post.call_args.kwargs["json"]
        self.assertFalse(body["store"])
        self.assertNotIn("test-key", str(body))
        post.return_value.status_code = 401
        with self.assertRaisesRegex(ValueError, "rejected"):
            explain_window({}, "test-key")
        post.side_effect = requests.Timeout()
        with self.assertRaisesRegex(ValueError, "timed out"):
            explain_window({}, "test-key")


if __name__ == "__main__":
    unittest.main()
