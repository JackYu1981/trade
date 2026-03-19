from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from trade.data.cache import cache_path_for_request
from trade.data.downloader import download_market_data
from trade.data.providers import CachePolicy, DownloadRequest, ProviderCapabilities, ProviderRegistry, ProviderSpec
from trade.data.provider_config import ProviderSettings


class FakeProvider:
    spec = ProviderSpec(
        provider_id="fake",
        name="Fake Historical Provider",
        capabilities=ProviderCapabilities(
            supports_history=True,
            supports_realtime=False,
            supports_period=True,
            supports_start_end=True,
            cacheable=True,
            intervals=("15m",),
            asset_classes=("forex",),
        ),
    )

    def __init__(self) -> None:
        self.calls = 0
        self.last_settings: ProviderSettings | None = None

    def download_rows(self, request: DownloadRequest, settings: ProviderSettings | None = None) -> list[dict[str, str | float]]:
        self.calls += 1
        self.last_settings = settings
        return [
            {
                "timestamp": "2026-01-01T00:00:00",
                "open": 1.1,
                "high": 1.11,
                "low": 1.09,
                "close": 1.105,
                "volume": 1000.0,
            }
        ]


class DataDownloaderTests(unittest.TestCase):
    def test_cache_path_uses_provider_symbol_interval_and_scope(self) -> None:
        request = DownloadRequest(
            provider="yfinance",
            symbol="EURUSD=X",
            interval="15m",
            start="2026-01-01",
            end="2026-01-31",
        )

        path = cache_path_for_request(request, CachePolicy(cache_dir=Path("/tmp/cache")))

        self.assertEqual(
            path,
            Path("/tmp/cache/yfinance/EURUSD_X/15m/start-2026_01_01_end-2026_01_31.csv"),
        )

    def test_download_market_data_uses_cache_on_repeated_request(self) -> None:
        provider = FakeProvider()
        registry = ProviderRegistry()
        registry.register(provider)

        with TemporaryDirectory() as tmp_dir:
            request = DownloadRequest(provider="fake", symbol="EURUSD=X", interval="15m", period="5d")
            policy = CachePolicy(cache_dir=Path(tmp_dir) / "cache")
            output_path = Path(tmp_dir) / "out" / "eurusd.csv"

            first_path = download_market_data(request, output_path=output_path, cache_policy=policy, registry=registry)
            second_path = download_market_data(request, output_path=output_path, cache_policy=policy, registry=registry)

            self.assertEqual(first_path, output_path)
            self.assertEqual(second_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("timestamp,open,high,low,close,volume", output_path.read_text(encoding="utf-8"))

        self.assertEqual(provider.calls, 1)

    def test_download_market_data_passes_provider_settings(self) -> None:
        provider = FakeProvider()
        registry = ProviderRegistry()
        registry.register(provider)

        with TemporaryDirectory() as tmp_dir:
            request = DownloadRequest(provider="fake", symbol="EURUSD=X", interval="15m", period="5d")
            output_path = Path(tmp_dir) / "eurusd.csv"

            download_market_data(
                request,
                output_path=output_path,
                cache_policy=CachePolicy(enabled=False),
                provider_settings=ProviderSettings(symbol_map={"EURUSD=X": "FX_IDC:EURUSD"}),
                registry=registry,
            )

        self.assertIsNotNone(provider.last_settings)
        assert provider.last_settings is not None
        self.assertEqual(provider.last_settings.symbol_map["EURUSD=X"], "FX_IDC:EURUSD")


if __name__ == "__main__":
    unittest.main()
