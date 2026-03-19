from __future__ import annotations

from datetime import datetime
import unittest

from trade.data.provider_config import ProviderSettings, provider_settings_from_options, resolve_download_request, resolve_live_request
from trade.data.providers import (
    CredentialField,
    DownloadRequest,
    LiveDataRequest,
    MarketSnapshot,
    ProviderCapabilities,
    ProviderRegistry,
    ProviderSpec,
)
from trade.data.realtime import fetch_market_snapshot


class FakeLiveProvider:
    spec = ProviderSpec(
        provider_id="fake-live",
        name="Fake Live Provider",
        capabilities=ProviderCapabilities(
            supports_history=False,
            supports_realtime=True,
            supports_period=False,
            supports_start_end=False,
            cacheable=False,
            intervals=("tick", "1s"),
            asset_classes=("forex",),
            notes="Test-only realtime provider.",
        ),
    )

    settings = ProviderSettings()

    def fetch_snapshot(self, request: LiveDataRequest, settings: ProviderSettings | None = None) -> MarketSnapshot:
        resolved = resolve_live_request(request, settings)
        return MarketSnapshot(
            provider=request.provider,
            symbol=resolved.symbol,
            timestamp=datetime(2026, 1, 1, 0, 0, 0),
            price=1.2345,
            bid=1.2344,
            ask=1.2346,
            volume=10.0,
            metadata={"interval": resolved.interval or "tick"},
        )


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_lists_historical_provider_specs(self) -> None:
        from trade.data import yfinance_downloader  # noqa: F401
        from trade.data.providers import list_provider_specs

        specs = list_provider_specs()

        self.assertTrue(any(spec.provider_id == "yfinance" for spec in specs))

    def test_fetch_market_snapshot_uses_live_registry(self) -> None:
        registry = ProviderRegistry()
        registry.register_live(FakeLiveProvider())

        snapshot = fetch_market_snapshot(
            LiveDataRequest(provider="fake-live", symbol="EURUSD", interval="tick"),
            registry=registry,
        )

        self.assertEqual(snapshot.provider, "fake-live")
        self.assertEqual(snapshot.symbol, "EURUSD")
        self.assertEqual(snapshot.price, 1.2345)
        self.assertEqual(snapshot.metadata["interval"], "tick")

    def test_resolve_download_request_applies_symbol_and_interval_mapping(self) -> None:
        resolved = resolve_download_request(
            DownloadRequest(provider="akshare", symbol="EURUSD", interval="1h", period="30d"),
            settings=ProviderSettings(
                symbol_map={"EURUSD": "FX_EURUSD"},
                interval_map={"1h": "60m"},
                extra_params={"market": "forex"},
            ),
        )

        self.assertEqual(resolved.symbol, "FX_EURUSD")
        self.assertEqual(resolved.interval, "60m")
        self.assertEqual(resolved.extra_params["market"], "forex")

    def test_provider_settings_from_options_reads_env_and_mappings(self) -> None:
        import os

        original_value = os.environ.get("TUSHARE_TOKEN")
        os.environ["TUSHARE_TOKEN"] = "secret-token"
        try:
            settings = provider_settings_from_options(
                credential_fields=(CredentialField(name="token", env_var="TUSHARE_TOKEN", required=True),),
                option_values=["adj=qfq"],
                symbol_map_values=["EURUSD=FX_EURUSD"],
                interval_map_values=["1d=D"],
            )
        finally:
            if original_value is None:
                os.environ.pop("TUSHARE_TOKEN", None)
            else:
                os.environ["TUSHARE_TOKEN"] = original_value

        self.assertEqual(settings.credentials["token"], "secret-token")
        self.assertEqual(settings.extra_params["adj"], "qfq")
        self.assertEqual(settings.symbol_map["EURUSD"], "FX_EURUSD")
        self.assertEqual(settings.interval_map["1d"], "D")


if __name__ == "__main__":
    unittest.main()
