from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from trade.data.providers import DownloadRequest
from trade.data.yfinance_downloader import DownloadSpec, download_history_for_request, download_to_csv, normalize_history_rows


class YFinanceDownloaderTests(unittest.TestCase):
    def test_normalize_history_rows_converts_download_frame(self) -> None:
        frame = pd.DataFrame(
            {
                "Open": [1.1, 1.2],
                "High": [1.11, 1.21],
                "Low": [1.09, 1.19],
                "Close": [1.105, 1.205],
                "Volume": [1000, 1100],
            },
            index=pd.to_datetime(["2026-01-01T00:00:00", "2026-01-01T00:15:00"]),
        )
        frame.index.name = "Datetime"

        rows = normalize_history_rows(frame)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["timestamp"], "2026-01-01T00:00:00")
        self.assertEqual(rows[1]["close"], 1.205)

    def test_normalize_history_rows_flattens_multiindex_columns(self) -> None:
        frame = pd.DataFrame(
            {
                ("Open", "EURUSD=X"): [1.1],
                ("High", "EURUSD=X"): [1.11],
                ("Low", "EURUSD=X"): [1.09],
                ("Close", "EURUSD=X"): [1.105],
                ("Volume", "EURUSD=X"): [1000],
            },
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        frame.index.name = "Datetime"

        rows = normalize_history_rows(frame)

        self.assertEqual(rows[0]["high"], 1.11)

    @patch("trade.data.yfinance_downloader.yf.download")
    def test_download_to_csv_writes_standardized_output(self, mock_download: object) -> None:
        frame = pd.DataFrame(
            {
                "Open": [1.1],
                "High": [1.11],
                "Low": [1.09],
                "Close": [1.105],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2026-01-01T00:00:00"]),
        )
        frame.index.name = "Datetime"
        mock_download.return_value = frame

        with TemporaryDirectory() as tmp_dir:
            path = download_to_csv(
                DownloadSpec(ticker="EURUSD=X", interval="15m", period="5d"),
                Path(tmp_dir) / "eurusd_15m.csv",
            )
            contents = path.read_text(encoding="utf-8")

        self.assertIn("timestamp,open,high,low,close,volume", contents)
        self.assertIn("2026-01-01T00:00:00,1.1,1.11,1.09,1.105,1000.0", contents)

    @patch("trade.data.yfinance_downloader.yf.download")
    def test_download_history_for_request_uses_symbol_interval_and_period(self, mock_download: object) -> None:
        frame = pd.DataFrame({"Open": [1.1], "High": [1.11], "Low": [1.09], "Close": [1.105]}, index=pd.to_datetime(["2026-01-01T00:00:00"]))
        frame.index.name = "Datetime"
        mock_download.return_value = frame

        download_history_for_request(
            DownloadRequest(provider="yfinance", symbol="EURUSD=X", interval="1h", period="30d")
        )

        _, kwargs = mock_download.call_args
        self.assertEqual(kwargs["tickers"], "EURUSD=X")
        self.assertEqual(kwargs["interval"], "1h")
        self.assertEqual(kwargs["period"], "30d")


if __name__ == "__main__":
    unittest.main()
