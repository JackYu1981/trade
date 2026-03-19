from __future__ import annotations

import unittest

from trade.data.standards import normalize_symbol, normalize_timeframe


class DataStandardsTests(unittest.TestCase):
    def test_normalize_symbol_handles_forex_aliases(self) -> None:
        self.assertEqual(normalize_symbol("eurusd"), "EUR/USD")
        self.assertEqual(normalize_symbol("EURUSD=X"), "EUR/USD")
        self.assertEqual(normalize_symbol("eur_usd"), "EUR/USD")

    def test_normalize_timeframe_handles_common_aliases(self) -> None:
        self.assertEqual(normalize_timeframe("60min"), "1h")
        self.assertEqual(normalize_timeframe("daily"), "1d")
        self.assertEqual(normalize_timeframe("15m"), "15m")


if __name__ == "__main__":
    unittest.main()
