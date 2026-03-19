from __future__ import annotations

from datetime import datetime, timedelta
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from trade.models import BacktestResult, DataQualityIssue, DataQualityReport, MarketBar, Trade
from trade.reporting.html_report import render_html_report
from trade.reporting.text_report import render_json_report, render_text_report


class ReportingTests(unittest.TestCase):
    def test_render_text_report_includes_data_quality_section(self) -> None:
        result = BacktestResult(
            symbol="EUR/USD",
            timeframe="1h",
            strategy_id="demo.multi_timeframe_ma",
            initial_cash=10_000.0,
            final_cash=10_000.0,
            trades=[],
            equity_curve=[10_000.0, 10_000.0],
            decisions=[
                {"timestamp": "2026-01-01T00:00:00", "action": "HOLD", "rule_results": []},
                {"timestamp": "2026-01-01T01:00:00", "action": "HOLD", "rule_results": []},
            ],
        )
        report = DataQualityReport(
            symbol="EUR/USD",
            timeframe="1h",
            bar_count=10,
            issues=[DataQualityIssue(code="time_gaps", severity="warning", count=1, message="Detected 1 timestamp gap.")],
        )

        rendered = render_text_report(result, data_quality_report=report)

        self.assertIn("Data Quality:", rendered)
        self.assertIn("Normalized symbol/timeframe: EUR/USD / 1h", rendered)
        self.assertIn("WARNING time_gaps", rendered)

    def test_render_json_report_includes_data_quality_payload(self) -> None:
        result = BacktestResult(
            symbol="EUR/USD",
            timeframe="1h",
            strategy_id="demo.multi_timeframe_ma",
            initial_cash=10_000.0,
            final_cash=10_001.0,
            trades=[
                Trade(
                    side="BUY",
                    entry_time=datetime(2026, 1, 1, 0, 0),
                    entry_price=1.1,
                    exit_time=datetime(2026, 1, 1, 1, 0),
                    exit_price=1.1001,
                    pnl=1.0,
                )
            ],
            equity_curve=[10_000.0, 10_001.0],
            decisions=[
                {"timestamp": "2026-01-01T00:00:00", "action": "BUY", "rule_results": []},
                {"timestamp": "2026-01-01T01:00:00", "action": "SELL", "rule_results": []},
            ],
        )
        report = DataQualityReport(symbol="EUR/USD", timeframe="1h", bar_count=10, issues=[])

        rendered = render_json_report(result, data_quality_report=report)

        self.assertIn('"data_quality"', rendered)
        self.assertIn('"bar_count": 10', rendered)

    def test_render_html_report_includes_svg_and_trade_table(self) -> None:
        result = BacktestResult(
            symbol="EUR/USD",
            timeframe="15m",
            strategy_id="demo.multi_timeframe_ma",
            initial_cash=10_000.0,
            final_cash=10_001.0,
            trades=[
                Trade(
                    side="BUY",
                    entry_time=datetime(2026, 1, 1, 0, 0),
                    entry_price=1.1,
                    exit_time=datetime(2026, 1, 1, 0, 15),
                    exit_price=1.1001,
                    pnl=1.0,
                )
            ],
            equity_curve=[10_000.0 + index for index in range(220)],
            decisions=[
                {"timestamp": "2026-01-01T00:00:00", "action": "BUY", "rule_results": []},
                {"timestamp": "2026-01-01T00:15:00", "action": "SELL", "rule_results": []},
            ],
        )
        report = DataQualityReport(symbol="EUR/USD", timeframe="15m", bar_count=220, issues=[])

        bars = []
        for index in range(220):
            close = 1.1000 + (0.00004 * index)
            bars.append(
                MarketBar(
                    datetime(2026, 1, 1, 0, 0) + timedelta(minutes=15 * index),
                    "EUR/USD",
                    "15m",
                    close - 0.0001,
                    close + 0.0003,
                    close - 0.0003,
                    close,
                    1000 + index,
                )
            )

        rendered = render_html_report(result, bars=bars, data_quality_report=report)

        self.assertIn("<html", rendered)
        self.assertIn("<h1>demo</h1>", rendered)
        self.assertIn("Candles And Trades", rendered)
        self.assertIn("plotly", rendered.lower())
        self.assertIn("Execution Log", rendered)
        self.assertIn("rgba(22, 163, 74, 0.10)", rendered)
        self.assertIn("MA60", rendered)
        self.assertIn('"scrollZoom": false', rendered)
        self.assertIn('"displayModeBar": false', rendered)
        self.assertIn('"dragmode":"pan"', rendered)
        self.assertIn('"type":"linear"', rendered)
        self.assertIn('"range"', rendered)
        self.assertIn("trade-report-chart", rendered)
        self.assertIn("chart-toolbar", rendered)
        self.assertIn("chart-analysis-box", rendered)
        self.assertIn("chart-selection-overlay", rendered)
        self.assertIn("selection-summary", rendered)
        self.assertIn("display: none", rendered)
        self.assertIn("chart-tool-pan", rendered)
        self.assertIn("chart-tool-select", rendered)
        self.assertIn("chart-tool-zoom", rendered)
        self.assertIn("chart-tool-home", rendered)
        self.assertIn("gd.addEventListener('wheel'", rendered)
        self.assertIn("Bars:", rendered)
        self.assertIn("Range:", rendered)
        self.assertIn("setMode('select')", rendered)
        self.assertIn("setMode('pan')", rendered)
        self.assertIn("resetView()", rendered)
        self.assertIn("showSelectionSummary", rendered)
        self.assertIn("hideSelectionSummary", rendered)
        self.assertIn("updateSelectionOverlay", rendered)
        self.assertIn("updateSelectionSummary", rendered)
        self.assertIn("mode: 'xzoom'", rendered)
        self.assertIn("mode: 'yzoom'", rendered)
        self.assertIn("hovertemplate", rendered)
        self.assertIn('"open"', rendered)
        self.assertIn('"close"', rendered)

    def test_cli_can_write_html_report(self) -> None:
        import subprocess

        with TemporaryDirectory() as tmp_dir:
            command = [
                ".venv/bin/python",
                "-m",
                "trade.cli",
                "examples/eurusd_1h_demo.csv",
                "--symbol",
                "EURUSD=X",
                "--timeframe",
                "60min",
                "--format",
                "html",
            ]
            completed = subprocess.run(
                command,
                cwd=Path.cwd(),
                env={**os.environ, "PYTHONPATH": "src"},
                check=True,
                capture_output=True,
                text=True,
            )

            output_path = Path(completed.stdout.strip())
            self.assertTrue(str(output_path).endswith("reports/demo-multi_timeframe_ma-EUR-USD-1h.html"))
            self.assertTrue(output_path.exists())
            self.assertIn("Trade Backtest Report", output_path.read_text(encoding="utf-8"))
