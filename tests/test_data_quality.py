from __future__ import annotations

from datetime import datetime
import unittest

from trade.data.quality import inspect_bars
from trade.models import MarketBar


class DataQualityTests(unittest.TestCase):
    def test_inspect_bars_reports_duplicate_and_gap_issues(self) -> None:
        bars = [
            MarketBar(datetime(2026, 1, 1, 0, 0), "EUR/USD", "15m", 1.1, 1.11, 1.09, 1.105, 1000),
            MarketBar(datetime(2026, 1, 1, 0, 0), "EUR/USD", "15m", 1.1, 1.11, 1.09, 1.106, 1000),
            MarketBar(datetime(2026, 1, 1, 0, 45), "EUR/USD", "15m", 1.2, 1.21, 1.19, 1.205, 1000),
        ]

        report = inspect_bars(bars)
        codes = {issue.code for issue in report.issues}

        self.assertEqual(report.symbol, "EUR/USD")
        self.assertEqual(report.timeframe, "15m")
        self.assertIn("duplicate_timestamps", codes)
        self.assertIn("time_gaps", codes)

    def test_inspect_bars_reports_invalid_ohlc(self) -> None:
        bars = [
            MarketBar(datetime(2026, 1, 1, 0, 0), "EUR/USD", "1h", 1.1, 1.09, 1.08, 1.11, 1000),
        ]

        report = inspect_bars(bars)

        self.assertEqual(report.issues[0].code, "invalid_ohlc")


if __name__ == "__main__":
    unittest.main()
