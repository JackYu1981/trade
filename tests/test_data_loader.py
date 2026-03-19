from __future__ import annotations

from pathlib import Path
import unittest

from trade.data.csv_loader import load_ohlcv_csv


class CsvLoaderTests(unittest.TestCase):
    def test_load_ohlcv_csv_returns_sorted_bars(self) -> None:
        bars = load_ohlcv_csv(
            Path("examples/eurusd_1h_demo.csv"),
            symbol="eurusd",
            timeframe="60min",
        )

        self.assertEqual(len(bars), 10)
        self.assertEqual(bars[0].close, 1.1000)
        self.assertEqual(bars[-1].close, 1.1005)
        self.assertEqual(bars[0].symbol, "EUR/USD")
        self.assertEqual(bars[0].timeframe, "1h")


if __name__ == "__main__":
    unittest.main()
