import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.metrics import TICKERS, build_snapshot, publish


TODAY = date(2026, 11, 21)


def sample(ticker):
    return [
        {"symbol": ticker, "timestamp": "2026-11-19T05:00:00Z", "close": 98},
        {"symbol": ticker, "timestamp": "2026-11-18T05:00:00Z", "close": 100},
    ]


class DailyChangeTests(unittest.TestCase):
    def test_common_dates_and_percent_units_without_raw_prices(self):
        result = build_snapshot(sample, TODAY)
        self.assertEqual(result["date"], "2026-11-19")
        self.assertEqual(result["previousDate"], "2026-11-18")
        self.assertEqual(result["changes"], dict.fromkeys(TICKERS, -2))
        self.assertEqual(set(result), {"date", "previousDate", "basis", "source", "changes"})

    def test_partial_coverage_or_invalid_input_fails_closed(self):
        for patch in (
            {"timestamp": "2026-11-20T05:00:00Z"},
            {"timestamp": "2026-11-18T05:00:00Z"},
            {"timestamp": "2026-11-21T05:00:00Z"},
            {"close": 0}, {"close": float("nan")}, {"is_gap": True}, {"symbol": "XYZ"},
        ):
            def altered(ticker):
                rows = sample(ticker)
                if ticker == "IBM":
                    rows[0].update(patch)
                return rows

            with self.subTest(patch=patch), self.assertRaises(ValueError):
                build_snapshot(altered, TODAY)

    def test_stale_series_cannot_publish(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            build_snapshot(sample, date(2026, 12, 1))

    def test_older_file_cannot_replace_current_snapshot(self):
        fresh = build_snapshot(sample, TODAY)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "metrics.json"
            publish(fresh, target)
            original = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "newer"):
                publish({**fresh, "date": "2026-11-17"}, target)
            self.assertEqual(target.read_bytes(), original)
            publish(fresh, target)
            self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
