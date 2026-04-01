from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from html import escape
import json

from plotly import graph_objects as go
from plotly.io import to_html
from trade.analysis.baseline import DEFAULT_BODY_SWING_WINDOW, build_window_legs, default_fish_window_config
from trade.analysis.summary import analyze_backtest
from trade.indicators.moving_average import moving_average
from trade.models import BacktestResult, DataQualityReport, MarketBar


DEFAULT_VISIBLE_BAR_COUNT = 60
DEFAULT_PRICE_RANGE_MULTIPLIER = 3.0
DISPLAY_TIMEZONE_OFFSET_HOURS = 8


def _strategy_display_name(strategy_id: str) -> str:
    return strategy_id.split(".", 1)[0] if "." in strategy_id else strategy_id


def render_html_report(
    result: BacktestResult,
    bars: list[MarketBar],
    data_quality_report: DataQualityReport | None = None,
) -> str:
    analysis = analyze_backtest(result)
    summary = analysis.summary
    payload = {
        "analysis": {
            "summary": analysis.summary,
            "curve_metrics": analysis.curve_metrics,
            "blocked_action_counts": analysis.blocked_action_counts,
            "top_blocked_reasons": analysis.top_blocked_reasons,
            "suggestions": analysis.suggestions,
        },
        "strategy": {
            "id": result.strategy_id,
            "name": result.strategy_name,
            "description": result.strategy_description,
            "parameters": result.strategy_parameters,
        },
        "data_quality": _data_quality_payload(data_quality_report),
        "trades": [asdict(trade) for trade in result.trades],
    }
    net_pnl = float(summary['net_pnl'])
    total_return = float(summary['total_return_pct'])
    sharpe = float(summary['sharpe'])
    summary_cards = [
        ("Net PnL", f"{net_pnl:.5f}", "positive" if net_pnl >= 0 else "negative"),
        ("Total Return", f"{total_return:.2%}", "positive" if total_return >= 0 else "negative"),
        ("Max Drawdown", f"{float(summary['max_drawdown']):.2%}", "negative" if float(summary['max_drawdown']) > 0.02 else ""),
        ("Sharpe", f"{sharpe:.2f}", "positive" if sharpe > 1 else ("negative" if sharpe < 0 else "")),
        ("Trades", str(summary["trade_count"]), ""),
        ("Win Rate", f"{float(summary['win_rate']):.2%}", "positive" if float(summary['win_rate']) > 0.5 else ("negative" if float(summary['win_rate']) < 0.4 else "")),
    ]
    trades_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(trade.side)}</td>"
            f"<td>{escape(trade.entry_time.isoformat())}</td>"
            f"<td>{trade.entry_price:.5f}</td>"
            f"<td>{escape(trade.exit_time.isoformat())}</td>"
            f"<td>{trade.exit_price:.5f}</td>"
            f"<td class=\"{'positive' if trade.pnl >= 0 else 'negative'}\">{trade.pnl:.5f}</td>"
            "</tr>"
        )
        for trade in result.trades
    ) or "<tr><td colspan=\"6\">No completed trades</td></tr>"
    suggestions_html = "\n".join(f"<li>{escape(item)}</li>" for item in analysis.suggestions)
    strategy_parameters_html = "\n".join(
        f"<li><strong>{escape(str(key))}</strong>: {escape(str(value))}</li>"
        for key, value in result.strategy_parameters.items()
    ) or "<li>No strategy parameters recorded</li>"
    blocked_html = "\n".join(
        f"<li><strong>{escape(reason)}</strong>: {count}</li>"
        for reason, count in analysis.top_blocked_reasons
    ) or "<li>No blocked reasons recorded</li>"
    data_quality_html = _data_quality_list(data_quality_report)
    json_payload = escape(json.dumps(payload, indent=2, default=str))
    display_bars = [_display_bar(bar) for bar in bars]
    chart_html = _render_plotly_chart(result, bars, display_bars)
    equity_chart_html = _render_equity_chart(result, display_bars)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Trade Backtest Report</title>
  <style>
    :root {{
      --bg: #0f1117;
      --panel: #181b23;
      --panel-alt: #1e2230;
      --ink: #e2e8f0;
      --muted: #8892a4;
      --line: rgba(148, 163, 184, 0.12);
      --accent: #38bdf8;
      --accent-dim: rgba(56, 189, 248, 0.10);
      --positive: #4ade80;
      --negative: #f87171;
      --positive-bg: rgba(74, 222, 128, 0.08);
      --negative-bg: rgba(248, 113, 113, 0.08);
      --shadow: 0 1px 3px rgba(0,0,0,0.3), 0 8px 32px rgba(0,0,0,0.2);
      --radius: 16px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: var(--ink);
      background: var(--bg);
      -webkit-font-smoothing: antialiased;
    }}
    main {{
      width: min(1360px, calc(100vw - 40px));
      margin: 28px auto 64px;
      display: grid;
      gap: 16px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 32px 32px 28px;
      display: grid;
      gap: 16px;
      background: linear-gradient(135deg, var(--panel) 0%, var(--panel-alt) 100%);
      border-top: 1px solid rgba(56, 189, 248, 0.15);
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 11px;
      font-weight: 600;
      color: var(--accent);
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #f8fafc;
    }}
    h2 {{
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      color: #f1f5f9;
    }}
    .subtle {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 10px;
      margin-top: 4px;
    }}
    .card {{
      padding: 16px 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--panel-alt);
      transition: border-color 150ms ease, background 150ms ease;
    }}
    .card:hover {{
      border-color: rgba(56, 189, 248, 0.2);
      background: rgba(56, 189, 248, 0.04);
    }}
    .card.card-positive {{
      border-color: rgba(74, 222, 128, 0.18);
      background: var(--positive-bg);
    }}
    .card.card-negative {{
      border-color: rgba(248, 113, 113, 0.18);
      background: var(--negative-bg);
    }}
    .label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 500;
      color: var(--muted);
    }}
    .value {{
      margin-top: 8px;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.01em;
      font-variant-numeric: tabular-nums;
    }}
    .card-positive .value {{ color: var(--positive); }}
    .card-negative .value {{ color: var(--negative); }}
    .panel {{
      padding: 24px;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 16px;
    }}
    .chart-shell {{
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: linear-gradient(180deg, var(--panel-alt), var(--panel));
      overflow: hidden;
      position: relative;
    }}
    .equity-shell {{
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 8px;
      background: linear-gradient(180deg, var(--panel-alt), var(--panel));
      overflow: hidden;
      position: relative;
    }}
    .chart-toolbar {{
      position: absolute;
      top: 16px;
      right: 16px;
      display: flex;
      gap: 4px;
      z-index: 3;
      padding: 4px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(24, 27, 35, 0.92);
      box-shadow: 0 4px 16px rgba(0,0,0,0.3);
      backdrop-filter: blur(12px);
    }}
    .chart-hover-readout {{
      position: absolute;
      top: 0;
      left: 0;
      z-index: 3;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      gap: 1px;
      color: var(--accent);
      font-size: 12px;
      line-height: 1.3;
    }}
    .chart-hover-readout .hover-title {{
      color: inherit;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .chart-hover-readout .hover-line {{
      color: inherit;
      font-weight: 600;
      font-size: 12px;
    }}
    .chart-hover-readout .hover-values {{
      display: flex;
      gap: 18px;
      color: inherit;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .chart-hover-readout .hover-values span {{
      min-width: 86px;
    }}
    .chart-tool {{
      width: 32px;
      height: 32px;
      border: 1px solid transparent;
      border-radius: 8px;
      background: transparent;
      color: var(--muted);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 120ms ease;
    }}
    .chart-tool:hover {{
      background: rgba(56, 189, 248, 0.08);
      color: var(--ink);
    }}
    .chart-tool.active {{
      background: var(--accent);
      color: var(--bg);
      border-color: var(--accent);
    }}
    .chart-analysis-box {{
      position: absolute;
      min-width: 180px;
      max-width: 240px;
      z-index: 3;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(24, 27, 35, 0.96);
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      backdrop-filter: blur(12px);
      display: none;
      font-size: 13px;
      color: var(--ink);
    }}
    .chart-analysis-box strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent);
    }}
    .chart-analysis-box .empty {{
      color: var(--muted);
    }}
    .chart-selection-overlay {{
      position: absolute;
      background: transparent;
      pointer-events: none;
      z-index: 2;
      display: none;
      inset: 0;
    }}
    .chart-selection-line {{
      position: absolute;
      display: none;
      pointer-events: none;
      background-repeat: repeat;
    }}
    .chart-selection-line.vertical {{
      width: 1px;
      background-image: var(--selection-vertical-stroke, repeating-linear-gradient(
        to bottom,
        rgba(56, 189, 248, 0.85) 0 8px,
        transparent 8px 14px
      ));
    }}
    .chart-selection-line.horizontal {{
      height: 1px;
      background-image: var(--selection-horizontal-stroke, repeating-linear-gradient(
        to right,
        rgba(56, 189, 248, 0.85) 0 8px,
        transparent 8px 14px
      ));
    }}
    .chart-crosshair-line {{
      position: absolute;
      pointer-events: none;
      z-index: 2;
      display: none;
      background-repeat: repeat;
    }}
    .chart-crosshair-line.x {{
      height: 1px;
      background-image: repeating-linear-gradient(
        to right,
        rgba(56, 189, 248, 0.5) 0 6px,
        transparent 6px 12px
      );
    }}
    .chart-crosshair-line.y {{
      width: 1px;
      background-image: repeating-linear-gradient(
        to bottom,
        rgba(56, 189, 248, 0.5) 0 6px,
        transparent 6px 12px
      );
    }}
    .chart-axis-label {{
      position: absolute;
      z-index: 3;
      pointer-events: none;
      display: none;
      padding: 2px 8px;
      border-radius: 6px;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.25);
      color: var(--accent);
      font-size: 11px;
      font-weight: 500;
      font-variant-numeric: tabular-nums;
      line-height: 1.1;
      white-space: nowrap;
    }}
    .chart-interaction-layer {{
      position: absolute;
      z-index: 2;
      display: none;
      background: transparent;
    }}
    .js-plotly-plot .plotly .hoverlayer .hovertext {{
      display: none;
    }}
    .js-plotly-plot .plotly .hoverlayer .axistext {{
      display: none;
    }}
    ul {{
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
    }}
    ul li strong {{
      color: var(--ink);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
    }}
    th, td {{
      padding: 10px 12px;
      text-align: left;
    }}
    th {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      font-weight: 600;
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      background: var(--panel);
    }}
    td {{
      border-bottom: 1px solid rgba(148, 163, 184, 0.06);
    }}
    tbody tr:hover {{
      background: rgba(56, 189, 248, 0.03);
    }}
    .table-scroll {{
      max-height: 420px;
      overflow-y: auto;
      border-radius: 8px;
      border: 1px solid var(--line);
    }}
    .table-scroll::-webkit-scrollbar {{
      width: 6px;
    }}
    .table-scroll::-webkit-scrollbar-track {{
      background: transparent;
    }}
    .table-scroll::-webkit-scrollbar-thumb {{
      background: rgba(148, 163, 184, 0.2);
      border-radius: 3px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
      font-size: 11px;
      line-height: 1.5;
      color: var(--muted);
      padding: 16px;
      border-radius: 8px;
      background: var(--panel-alt);
      border: 1px solid var(--line);
      max-height: 400px;
      overflow-y: auto;
    }}
    .positive {{ color: var(--positive); }}
    .negative {{ color: var(--negative); }}
    details {{
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }}
    details summary {{
      padding: 12px 16px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      color: var(--muted);
      background: var(--panel-alt);
      transition: color 120ms;
    }}
    details summary:hover {{
      color: var(--ink);
    }}
    details[open] summary {{
      border-bottom: 1px solid var(--line);
    }}
    details pre {{
      border: none;
      border-radius: 0;
    }}
    @media (max-width: 900px) {{
      .split {{
        grid-template-columns: 1fr;
      }}
      .grid {{
        grid-template-columns: repeat(3, 1fr);
      }}
      main {{
        width: min(100vw - 20px, 1360px);
        margin-top: 20px;
      }}
    }}
    @media (max-width: 600px) {{
      .grid {{
        grid-template-columns: repeat(2, 1fr);
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">Research Report</div>
      <h1>{escape(_strategy_display_name(str(summary['strategy_id'])))}</h1>
      <div class="subtle">{escape(result.strategy_name)} · {escape(str(summary['symbol']))} · {escape(str(summary['timeframe']))}</div>
      <div class="subtle">{escape(result.strategy_description)}</div>
      <div class="grid">
        {"".join(f'<div class="card{" card-" + cls if cls else ""}"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>' for label, value, cls in summary_cards)}
      </div>
    </section>

    <section class="panel">
      <div class="eyebrow">Charts</div>
      <h2>Candles And Trades</h2>
      <div class="chart-shell">
        <div class="chart-toolbar" aria-label="Chart tools">
          <button id="chart-tool-pan" class="chart-tool active" type="button" title="Pan" aria-label="Pan">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2v20M2 12h20"/>
              <path d="m8 6 4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4"/>
            </svg>
          </button>
          <button id="chart-tool-select" class="chart-tool" type="button" title="Box Select" aria-label="Box Select">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>
              <rect x="8" y="8" width="8" height="8" rx="1"/>
            </svg>
          </button>
          <button id="chart-tool-zoom" class="chart-tool" type="button" title="Zoom" aria-label="Zoom">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="6"/>
              <path d="m20 20-4.2-4.2M11 8v6M8 11h6"/>
            </svg>
          </button>
          <button id="chart-tool-home" class="chart-tool" type="button" title="Reset View" aria-label="Reset View">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 10.5 12 3l9 7.5"/>
              <path d="M5.5 9.5V21h13V9.5"/>
              <path d="M9 21v-6h6v6"/>
            </svg>
          </button>
        </div>
        <div id="chart-hover-readout" class="chart-hover-readout" aria-hidden="true">
          <div class="hover-line">&nbsp;</div>
        </div>
        <div id="selection-summary" class="chart-analysis-box">
          <strong>Selection</strong>
          <div class="empty">Use Box Select to inspect bar count and price range.</div>
        </div>
        <div id="chart-crosshair-x" class="chart-crosshair-line x" aria-hidden="true"></div>
        <div id="chart-crosshair-y" class="chart-crosshair-line y" aria-hidden="true"></div>
        <div id="chart-crosshair-x-label" class="chart-axis-label" aria-hidden="true"></div>
        <div id="chart-crosshair-y-label" class="chart-axis-label" aria-hidden="true"></div>
        <div id="chart-interaction-layer" class="chart-interaction-layer" aria-hidden="true"></div>
        <div id="chart-selection-overlay" class="chart-selection-overlay" aria-hidden="true">
          <div class="chart-selection-line vertical" data-edge="left"></div>
          <div class="chart-selection-line vertical" data-edge="right"></div>
          <div class="chart-selection-line horizontal" data-edge="top"></div>
          <div class="chart-selection-line horizontal" data-edge="bottom"></div>
        </div>
        {chart_html}
      </div>
      <div class="equity-shell">
        {equity_chart_html}
      </div>
    </section>

    <section class="panel split">
      <div>
        <div class="eyebrow">Strategy Contract</div>
        <h2>Execution Rules</h2>
        <ul>{strategy_parameters_html}</ul>
      </div>
      <div>
        <div class="eyebrow">Review</div>
        <h2>Strategy Notes</h2>
        <ul>{suggestions_html}</ul>
        <div class="eyebrow" style="margin-top:18px;">Blocked Reasons</div>
        <ul>{blocked_html}</ul>
      </div>
    </section>

    <section class="panel split">
      <div>
        <div class="eyebrow">Data Quality</div>
        <h2>Input Status</h2>
        <ul>{data_quality_html}</ul>
      </div>
      <div>
        <div class="eyebrow">Positioning</div>
        <h2>Execution Mode</h2>
        <ul>
          <li><strong>Position mode</strong>: {escape(str(result.strategy_parameters.get('position_mode', 'unspecified')))}</li>
          <li><strong>Trade count</strong>: {summary['trade_count']}</li>
          <li><strong>Sides observed</strong>: {escape(", ".join(sorted({trade.side for trade in result.trades})) if result.trades else "none")}</li>
        </ul>
      </div>
    </section>

    <section class="panel">
      <div class="eyebrow">Trades</div>
      <h2>Execution Log</h2>
      <div class="table-scroll" style="margin-top: 12px;">
      <table>
        <thead>
          <tr>
            <th>Side</th>
            <th>Entry Time</th>
            <th>Entry</th>
            <th>Exit Time</th>
            <th>Exit</th>
            <th>PnL</th>
          </tr>
        </thead>
        <tbody>
          {trades_html}
        </tbody>
      </table>
      </div>
    </section>

    <section class="panel">
      <div class="eyebrow">Payload</div>
      <h2>Structured Snapshot</h2>
      <details style="margin-top: 12px;">
        <summary>Expand JSON payload</summary>
        <pre>{json_payload}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


def _render_plotly_chart(result: BacktestResult, bars: list[MarketBar], display_bars: list[MarketBar]) -> str:
    fish_legs = build_window_legs(bars, default_fish_window_config(), body_swing_window=DEFAULT_BODY_SWING_WINDOW)
    fast_period = int(result.strategy_parameters.get("fast_period", 20))
    mid_period = int(result.strategy_parameters.get("mid_period", 60))
    fast_ma_values = moving_average(bars, period=fast_period)
    mid_ma_values = moving_average(bars, period=mid_period)
    bar_indices = list(range(len(display_bars)))
    timestamp_labels = [_display_label(bar.timestamp) for bar in display_bars]
    original_index_by_timestamp = {bar.timestamp.isoformat(): index for index, bar in enumerate(bars)}
    visible_bars = display_bars[-DEFAULT_VISIBLE_BAR_COUNT:] if len(display_bars) > DEFAULT_VISIBLE_BAR_COUNT else display_bars
    visible_lows = [bar.low for bar in visible_bars]
    visible_highs = [bar.high for bar in visible_bars]
    y_min = min(visible_lows) if visible_lows else 0.0
    y_max = max(visible_highs) if visible_highs else 1.0
    visible_span = max(y_max - y_min, 0.0005)
    padded_span = max(visible_span * DEFAULT_PRICE_RANGE_MULTIPLIER, 0.005)
    y_mid = (y_max + y_min) / 2
    visible_start_index = max(0, len(display_bars) - len(visible_bars))
    initial_x_range = [visible_start_index - 0.5, len(display_bars) - 0.5] if display_bars else None
    initial_y_range = [y_mid - (padded_span / 2), y_mid + (padded_span / 2)]
    figure = go.Figure()
    figure.add_trace(
        go.Candlestick(
            x=bar_indices,
            open=[bar.open for bar in display_bars],
            high=[bar.high for bar in display_bars],
            low=[bar.low for bar in display_bars],
            close=[bar.close for bar in display_bars],
            customdata=timestamp_labels,
            name="Price",
            increasing_line_color="#4ade80",
            decreasing_line_color="#f87171",
            hovertemplate=(
                "%{customdata}<br>"
                "Open=%{open:.5f}<br>"
                "High=%{high:.5f}<br>"
                "Low=%{low:.5f}<br>"
                "Close=%{close:.5f}<extra></extra>"
            ),
        ),
    )

    for leg in fish_legs:
        figure.add_vrect(
            x0=leg.start_index - 0.5,
            x1=leg.end_index + 0.5,
            fillcolor="rgba(22, 163, 74, 0.10)" if leg.direction == "up" else "rgba(220, 38, 38, 0.10)",
            line_width=0,
            layer="below",
        )
        if leg.body_start_index is not None:
            figure.add_vrect(
                x0=leg.body_start_index - 0.5,
                x1=leg.body_end_index + 0.5,
                fillcolor="rgba(0, 128, 0, 0.25)" if leg.direction == "up" else "rgba(178, 34, 34, 0.25)",
                line_width=0,
                layer="below",
            )

    if result.trades:
        trade_groups = [
            ("LONG", "entry", "Long Entry", "triangle-up", "#38bdf8", "Long entry"),
            ("LONG", "exit", "Long Exit", "triangle-down", "#f87171", "Long exit"),
            ("SHORT", "entry", "Short Entry", "triangle-down", "#f87171", "Short entry"),
            ("SHORT", "exit", "Short Exit", "triangle-up", "#38bdf8", "Short exit"),
        ]
        for side, event_kind, trace_name, symbol, color, hover_label in trade_groups:
            selected_trades = [trade for trade in result.trades if trade.side == side]
            if not selected_trades:
                continue
            if event_kind == "entry":
                indices = [original_index_by_timestamp[trade.entry_time.isoformat()] for trade in selected_trades]
                prices = [trade.entry_price for trade in selected_trades]
            else:
                indices = [original_index_by_timestamp[trade.exit_time.isoformat()] for trade in selected_trades]
                prices = [trade.exit_price for trade in selected_trades]

            figure.add_trace(
                go.Scatter(
                    x=indices,
                    y=prices,
                    mode="markers",
                    name=trace_name,
                    marker={
                        "size": 15,
                        "color": color,
                        "symbol": symbol,
                        "line": {"color": "#ffffff", "width": 1.5},
                    },
                    customdata=[timestamp_labels[index] for index in indices],
                    hovertemplate=f"{hover_label}<br>%{{customdata}}<br>Price=%{{y:.5f}}<extra></extra>",
                    showlegend=False,
                ),
            )

    figure.add_trace(
        go.Scatter(
            x=bar_indices,
            y=fast_ma_values,
            mode="lines",
            name=f"MA{fast_period}",
            line={"color": "#38bdf8", "width": 1.5},
            hoverinfo="skip",
        ),
    )

    figure.add_trace(
        go.Scatter(
            x=bar_indices,
            y=mid_ma_values,
            mode="lines",
            name=f"MA{mid_period}",
            line={"color": "#fbbf24", "width": 1.5},
            hoverinfo="skip",
        ),
    )

    figure.update_layout(
        template="plotly_dark",
        height=820,
        margin={"l": 24, "r": 24, "t": 58, "b": 24},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,34,48,0.6)",
        dragmode="pan",
        hovermode="x",
        font={"family": "Inter, -apple-system, sans-serif", "color": "#e2e8f0", "size": 11},
        showlegend=False,
    )
    figure.update_yaxes(
        tickformat=".5f",
        ticks="outside",
        automargin=True,
        fixedrange=False,
        autorange=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikecolor="rgba(56, 189, 248, 0.5)",
        gridcolor="rgba(148, 163, 184, 0.08)",
        range=initial_y_range,
    )
    figure.update_xaxes(
        showticklabels=True,
        type="linear",
        ticks="outside",
        automargin=True,
        autorange=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikecolor="rgba(56, 189, 248, 0.5)",
        gridcolor="rgba(148, 163, 184, 0.08)",
        rangeslider={"visible": False},
        range=initial_x_range,
    )
    post_script = """
    (function() {
        const gd = document.getElementById('{plot_id}');
      const summary = document.getElementById('selection-summary');
      const hoverReadout = document.getElementById('chart-hover-readout');
      const crosshairX = document.getElementById('chart-crosshair-x');
      const crosshairY = document.getElementById('chart-crosshair-y');
      const crosshairXLabel = document.getElementById('chart-crosshair-x-label');
      const crosshairYLabel = document.getElementById('chart-crosshair-y-label');
      const panButton = document.getElementById('chart-tool-pan');
      const selectButton = document.getElementById('chart-tool-select');
      const zoomButton = document.getElementById('chart-tool-zoom');
      const homeButton = document.getElementById('chart-tool-home');
      const interactionLayer = document.getElementById('chart-interaction-layer');
      const selectionOverlay = document.getElementById('chart-selection-overlay');
      const selectionLeftEdge = selectionOverlay ? selectionOverlay.querySelector('[data-edge="left"]') : null;
      const selectionRightEdge = selectionOverlay ? selectionOverlay.querySelector('[data-edge="right"]') : null;
      const selectionTopEdge = selectionOverlay ? selectionOverlay.querySelector('[data-edge="top"]') : null;
      const selectionBottomEdge = selectionOverlay ? selectionOverlay.querySelector('[data-edge="bottom"]') : null;
      const chartShell = gd.closest('.chart-shell');
      if (!gd) {
        return;
      }

      let axisDrag = null;
      let boxSelect = null;
      let selectedBox = null;
      let toolMode = 'pan';
      const bars = %s;
      const timestampLabels = bars.map((bar) => bar.timestamp);
      const initialLeft = %s;
      const initialRight = %s;
      const initialBottom = %s;
      const initialTop = %s;
      const selectionDragColor = 'rgba(37, 99, 235, 0.95)';
      const selectionSummaryDefault = '<strong>Selection</strong><div class="empty">Use Box Select to inspect bar count and price range.</div>';
      const hoverReadoutDefault = "<div class='hover-line'>&nbsp;</div>";

      function setActiveButton(mode) {
        if (!panButton || !selectButton || !zoomButton) {
          return;
        }
        for (const [button, targetMode] of [[panButton, 'pan'], [selectButton, 'select'], [zoomButton, 'zoom']]) {
          if (!button) {
            continue;
          }
          button.classList.toggle('active', mode === targetMode);
        }
      }

      function setMode(mode) {
        toolMode = mode;
        const nextDragMode = mode === 'zoom' ? 'zoom' : 'pan';
        Plotly.relayout(gd, { dragmode: nextDragMode, selections: [] });
        if (mode !== 'select' && summary) {
          hideSelectionSummary();
        }
        syncInteractionLayer(mode === 'select');
        if (mode !== 'select') {
          clearSelectionOverlay();
        }
        setActiveButton(mode);
      }

      function relayoutXRange(nextLeft, nextRight) {
        Plotly.relayout(gd, {
          'xaxis.range': [nextLeft, nextRight],
          selections: []
        });
        updateAxisTicks(gd, nextLeft, nextRight);
      }

      function relayoutYRange(nextBottom, nextTop) {
        Plotly.relayout(gd, {
          'yaxis.range': [nextBottom, nextTop],
          selections: []
        });
      }

      function resetView() {
        Plotly.relayout(gd, {
          dragmode: 'pan',
          'xaxis.range': [initialLeft, initialRight],
          'yaxis.range': [initialBottom, initialTop],
          selections: []
        });
        hideSelectionSummary();
        clearSelectionOverlay();
        setActiveButton('pan');
        updateAxisTicks(gd, initialLeft, initialRight);
      }

      function clearSelectionOverlay() {
        boxSelect = null;
        selectedBox = null;
        if (selectionOverlay) {
          selectionOverlay.style.display = 'none';
          selectionOverlay.style.width = '0px';
          selectionOverlay.style.height = '0px';
        }
        for (const edge of [selectionLeftEdge, selectionRightEdge, selectionTopEdge, selectionBottomEdge]) {
          if (edge) {
            edge.style.display = 'none';
          }
        }
        hideSelectionSummary();
      }

      function hideSelectionSummary() {
        if (!summary) {
          return;
        }
        summary.style.display = 'none';
        summary.innerHTML = selectionSummaryDefault;
      }

      function selectionColorForRange(startIndex, endIndex) {
        const startBar = bars[Math.min(startIndex, endIndex)];
        const endBar = bars[Math.max(startIndex, endIndex)];
        if (!startBar || !endBar) {
          return 'rgba(15, 118, 110, 0.95)';
        }
        return endBar.close >= startBar.close
          ? 'rgba(22, 163, 74, 0.95)'
          : 'rgba(220, 38, 38, 0.95)';
      }

      function updateSelectionStrokeColor(color) {
        if (!selectionOverlay) {
          return;
        }
        selectionOverlay.style.setProperty(
          '--selection-vertical-stroke',
          'repeating-linear-gradient(to bottom, ' + color + ' 0 8px, transparent 8px 14px)'
        );
        selectionOverlay.style.setProperty(
          '--selection-horizontal-stroke',
          'repeating-linear-gradient(to right, ' + color + ' 0 8px, transparent 8px 14px)'
        );
      }

      function showSelectionSummary(left, top, width) {
        if (!summary) {
          return;
        }
        const shell = summary.parentElement;
        const shellWidth = shell ? shell.clientWidth : 0;
        summary.style.display = 'block';
        const summaryWidth = summary.offsetWidth || 220;
        const desiredLeft = left + width + 12;
        const maxLeft = Math.max(12, shellWidth - summaryWidth - 12);
        summary.style.left = Math.min(desiredLeft, maxLeft) + 'px';
        summary.style.top = Math.max(72, top) + 'px';
      }

      function resetHoverReadout() {
        if (!hoverReadout) {
          return;
        }
        hoverReadout.innerHTML = hoverReadoutDefault;
        const geom = currentGeometry();
        hoverReadout.style.left = (geom.left + 20) + 'px';
        hoverReadout.style.top = (geom.top + 10) + 'px';
      }

      function getShellRect() {
        return chartShell ? chartShell.getBoundingClientRect() : gd.getBoundingClientRect();
      }

      function getCandleCenterX(indexValue) {
        const candle = gd.querySelectorAll('.boxlayer .trace.boxes path.box')[indexValue];
        if (!candle) {
          return null;
        }
        const shellRect = getShellRect();
        const candleRect = candle.getBoundingClientRect();
        return ((candleRect.left + candleRect.right) / 2) - shellRect.left;
      }

      function hideCrosshair() {
        for (const element of [crosshairX, crosshairY, crosshairXLabel, crosshairYLabel]) {
          if (element) {
            element.style.display = 'none';
          }
        }
      }

      function showCrosshair(index, localY, geom) {
        const clampedIndex = Math.min(Math.max(0, index), bars.length - 1);
        const centerX = indexToScreenX(clampedIndex, geom);
        const price = screenYToPrice(localY, geom);
        if (crosshairX) {
          crosshairX.style.display = 'block';
          crosshairX.style.left = geom.left + 'px';
          crosshairX.style.top = (localY - 0.5) + 'px';
          crosshairX.style.width = Math.max(0, geom.right - geom.left) + 'px';
        }
        if (crosshairY) {
          crosshairY.style.display = 'block';
          crosshairY.style.left = (centerX - 0.5) + 'px';
          crosshairY.style.top = geom.top + 'px';
          crosshairY.style.height = Math.max(0, geom.bottom - geom.top) + 'px';
        }
        if (crosshairXLabel) {
          crosshairXLabel.style.display = 'block';
          crosshairXLabel.textContent = timestampLabels[clampedIndex];
          crosshairXLabel.style.left = Math.max(geom.left, Math.min(centerX - 52, geom.right - 124)) + 'px';
          crosshairXLabel.style.top = (geom.bottom + 6) + 'px';
        }
        if (crosshairYLabel) {
          crosshairYLabel.style.display = 'block';
          crosshairYLabel.textContent = price.toFixed(5);
          crosshairYLabel.style.left = Math.max(8, geom.left - 74) + 'px';
          crosshairYLabel.style.top = Math.max(geom.top - 10, Math.min(localY - 9, geom.bottom - 22)) + 'px';
        }
      }

      function updateHoverReadout(point) {
        if (!hoverReadout || !point || !point.data || point.data.type !== 'candlestick') {
          return;
        }
        const xValue = String(point.customdata ?? timestampLabels[Number(point.pointNumber ?? 0)] ?? '');
        const pointNumber = Number(point.pointNumber ?? 0);
        const openValue = Number(point.open ?? point.data.open?.[pointNumber] ?? 0);
        const highValue = Number(point.high ?? point.data.high?.[pointNumber] ?? 0);
        const lowValue = Number(point.low ?? point.data.low?.[pointNumber] ?? 0);
        const closeValue = Number(point.close ?? point.data.close?.[pointNumber] ?? 0);
        hoverReadout.style.color = closeValue >= openValue ? '#4ade80' : '#f87171';
        hoverReadout.innerHTML =
          "<div class='hover-line'>" + xValue + "</div>" +
          "<div class='hover-values'><span>O " + openValue.toFixed(5) + "</span><span>H " + highValue.toFixed(5) + "</span></div>" +
          "<div class='hover-values'><span>C " + closeValue.toFixed(5) + "</span><span>L " + lowValue.toFixed(5) + "</span></div>";
      }

      function updateAxisTicks(targetGd, leftValue, rightValue) {
        if (!targetGd || !bars.length) {
          return;
        }
        const startIndex = Math.max(0, Math.floor(leftValue + 0.5));
        const endIndex = Math.min(bars.length - 1, Math.ceil(rightValue - 0.5));
        const visibleCount = Math.max(1, endIndex - startIndex + 1);
        const preferredTickCount = 8;
        const stepCandidates = [1, 2, 4, 8, 12, 24, 48, 96, 192, 384, 768];
        const step = stepCandidates.find((candidate) => Math.ceil(visibleCount / candidate) <= preferredTickCount) || stepCandidates[stepCandidates.length - 1];
        const tickvals = [];
        const ticktext = [];
        for (let index = startIndex; index <= endIndex; index += step) {
          tickvals.push(index);
          ticktext.push(timestampLabels[index].replace(' ', '<br>'));
        }
        if (tickvals[tickvals.length - 1] !== endIndex) {
          tickvals.push(endIndex);
          ticktext.push(timestampLabels[endIndex].replace(' ', '<br>'));
        }
        Plotly.relayout(targetGd, {
          'xaxis.tickmode': 'array',
          'xaxis.tickvals': tickvals,
          'xaxis.ticktext': ticktext,
        });
      }

      function syncInteractionLayer(enabled) {
        if (!interactionLayer) {
          return;
        }
        const geom = currentGeometry();
        interactionLayer.style.left = geom.left + 'px';
        interactionLayer.style.top = geom.top + 'px';
        interactionLayer.style.width = Math.max(0, geom.right - geom.left) + 'px';
        interactionLayer.style.height = Math.max(0, geom.bottom - geom.top) + 'px';
        interactionLayer.style.display = enabled ? 'block' : 'none';
        interactionLayer.style.pointerEvents = enabled ? 'auto' : 'none';
        interactionLayer.style.cursor = selectedBox ? 'move' : 'crosshair';
        if (!enabled) {
          hideCrosshair();
        }
      }

      function updateSelectionOverlay(left, top, width, height, color) {
        if (!selectionOverlay) {
          return;
        }
        updateSelectionStrokeColor(color || 'rgba(15, 118, 110, 0.95)');
        selectionOverlay.style.display = 'block';
        selectionOverlay.style.left = '0px';
        selectionOverlay.style.top = '0px';
        selectionOverlay.style.width = '100%%';
        selectionOverlay.style.height = '100%%';
        if (selectionLeftEdge) {
          selectionLeftEdge.style.display = 'block';
          selectionLeftEdge.style.left = (left - 0.5) + 'px';
          selectionLeftEdge.style.top = top + 'px';
          selectionLeftEdge.style.height = height + 'px';
        }
        if (selectionRightEdge) {
          selectionRightEdge.style.display = 'block';
          selectionRightEdge.style.left = (left + width - 0.5) + 'px';
          selectionRightEdge.style.top = top + 'px';
          selectionRightEdge.style.height = height + 'px';
        }
        if (selectionTopEdge) {
          selectionTopEdge.style.display = 'block';
          selectionTopEdge.style.left = left + 'px';
          selectionTopEdge.style.top = (top - 0.5) + 'px';
          selectionTopEdge.style.width = width + 'px';
        }
        if (selectionBottomEdge) {
          selectionBottomEdge.style.display = 'block';
          selectionBottomEdge.style.left = left + 'px';
          selectionBottomEdge.style.top = (top + height - 0.5) + 'px';
          selectionBottomEdge.style.width = width + 'px';
        }
      }

      function hitSelectedBox(localX, localY) {
        if (!selectedBox) {
          return false;
        }
        return (
          localX >= selectedBox.left &&
          localX <= selectedBox.left + selectedBox.width &&
          localY >= selectedBox.top &&
          localY <= selectedBox.top + selectedBox.height
        );
      }

      function hitSelectedBoxEdge(localX, localY) {
        if (!selectedBox) {
          return null;
        }
        const edgeTolerance = 8;
        const left = selectedBox.left;
        const right = selectedBox.left + selectedBox.width;
        const top = selectedBox.top;
        const bottom = selectedBox.top + selectedBox.height;
        const insideVertical = localY >= top && localY <= bottom;
        const insideHorizontal = localX >= left && localX <= right;

        if (Math.abs(localX - left) <= edgeTolerance && insideVertical) {
          return "left";
        }
        if (Math.abs(localX - right) <= edgeTolerance && insideVertical) {
          return "right";
        }
        if (Math.abs(localY - top) <= edgeTolerance && insideHorizontal) {
          return "top";
        }
        if (Math.abs(localY - bottom) <= edgeTolerance && insideHorizontal) {
          return "bottom";
        }
        return null;
      }

      function screenXToIndex(screenX, geom) {
        const axis = gd._fullLayout.xaxis;
        const plotX = screenX - geom.left;
        return axis.p2l(plotX);
      }

      function indexToScreenX(indexValue, geom) {
        const candleCenter = getCandleCenterX(indexValue);
        if (candleCenter !== null) {
          return candleCenter;
        }
        const axis = gd._fullLayout.xaxis;
        return geom.left + axis.l2p(indexValue);
      }

      function nearestBarIndexAtScreenX(screenX, geom) {
        return Math.min(Math.max(0, Math.round(screenXToIndex(screenX, geom))), bars.length - 1);
      }

      function boxGeometryFromIndices(startIndex, endIndex, top, height, geom) {
        const left = indexToScreenX(startIndex, geom);
        const right = indexToScreenX(endIndex, geom);
        return {
          left: Math.min(left, right),
          top,
          width: Math.max(1, Math.abs(right - left)),
          height,
        };
      }

      function screenYToPrice(screenY, geom) {
        const ratio = (geom.bottom - screenY) / (geom.bottom - geom.top || 1);
        const yRange = gd._fullLayout.yaxis.range;
        return yRange[0] + ((yRange[1] - yRange[0]) * ratio);
      }

      function updateSelectionSummary(startIndex, endIndex, startY, endY, geom, boxLeft, boxTop, boxWidth) {
        if (!summary) {
          return;
        }
        const topY = Math.max(geom.top, Math.min(startY, endY));
        const bottomY = Math.min(geom.bottom, Math.max(startY, endY));
        if (endIndex < startIndex || bottomY <= topY) {
          hideSelectionSummary();
          return;
        }

        const selectedBars = bars.slice(startIndex, endIndex + 1);
        const topPrice = screenYToPrice(topY, geom);
        const bottomPrice = screenYToPrice(bottomY, geom);
        const priceDiff = Math.abs(topPrice - bottomPrice);
        const pointsDiff = priceDiff / 0.0001;

        summary.innerHTML =
          '<strong>Selection</strong>' +
          '<div>Bars: ' + selectedBars.length + '</div>' +
          '<div>Range: ' + pointsDiff.toFixed(1) + ' pts</div>';
        const anchorLeft = boxLeft !== undefined ? boxLeft : (selectedBox ? selectedBox.left : 0);
        const anchorTop = boxTop !== undefined ? boxTop : (selectedBox ? selectedBox.top : 0);
        const anchorWidth = boxWidth !== undefined ? boxWidth : (selectedBox ? selectedBox.width : 0);
        showSelectionSummary(anchorLeft, anchorTop, anchorWidth);
      }

      function currentGeometry() {
        const full = gd._fullLayout;
        const shellRect = getShellRect();
        const gdRect = gd.getBoundingClientRect();
        const left = (gdRect.left - shellRect.left) + full.xaxis._offset;
        const right = left + full.xaxis._length;
        const top = (gdRect.top - shellRect.top) + full.yaxis._offset;
        const bottom = top + full.yaxis._length;
        return { left, right, top, bottom };
      }

      gd.addEventListener('wheel', function(event) {
        if (toolMode === 'select') {
          return;
        }
        const geom = currentGeometry();
        const shellRect = getShellRect();
        const localX = event.clientX - shellRect.left;
        const localY = event.clientY - shellRect.top;
        if (
          localX < geom.left ||
          localX > geom.right ||
          localY < geom.top ||
          localY > geom.bottom
        ) {
          return;
        }

        const width = geom.right - geom.left || 1;
        const pointerX = Math.min(Math.max(localX - geom.left, 0), width);
        const left = gd._fullLayout.xaxis.range[0];
        const right = gd._fullLayout.xaxis.range[1];
        const leftIndex = Number(left);
        const rightIndex = Number(right);
        const span = rightIndex - leftIndex;
        if (!Number.isFinite(span) || span <= 0) {
          return;
        }

        event.preventDefault();
        const zoomFactor = event.deltaY < 0 ? 0.85 : 1.15;
        const nextSpan = span * zoomFactor;
        const ratio = pointerX / width;
        const anchor = leftIndex + (span * ratio);
        const nextLeft = anchor - (nextSpan * ratio);
        const nextRight = anchor + (nextSpan * (1 - ratio));

        relayoutXRange(nextLeft, nextRight);
      }, { passive: false });

      gd.addEventListener('mousedown', function(event) {
        const rect = getShellRect();
        const geom = currentGeometry();
        const localX = event.clientX - rect.left;
        const localY = event.clientY - rect.top;
        const axisBand = 28;

        if (localX >= geom.left && localX <= geom.right && localY >= geom.bottom && localY <= geom.bottom + axisBand) {
          const left = Number(gd._fullLayout.xaxis.range[0]);
          const right = Number(gd._fullLayout.xaxis.range[1]);
          axisDrag = {
            mode: 'xzoom',
            startX: event.clientX,
            left,
            right,
          };
          event.preventDefault();
          return;
        }

        if (localX >= Math.max(0, geom.left - 60) && localX <= geom.left && localY >= geom.top && localY <= geom.bottom) {
          const bottom = gd._fullLayout.yaxis.range[0];
          const top = gd._fullLayout.yaxis.range[1];
          axisDrag = {
            mode: 'yzoom',
            startY: event.clientY,
            bottom,
            top,
          };
          event.preventDefault();
        }
      });

      if (interactionLayer) {
        interactionLayer.addEventListener('mousedown', function(event) {
          if (toolMode !== 'select') {
            return;
          }
          const rect = getShellRect();
          const geom = currentGeometry();
          const localX = event.clientX - rect.left;
          const localY = event.clientY - rect.top;
          const edge = hitSelectedBoxEdge(localX, localY);
          if (edge) {
            boxSelect = {
              mode: 'resize-' + edge,
              originalTop: selectedBox.top,
              originalHeight: selectedBox.height,
              startIndex: selectedBox.startIndex,
              endIndex: selectedBox.endIndex,
              previewStartIndex: selectedBox.startIndex,
              previewEndIndex: selectedBox.endIndex,
              previewLeft: selectedBox.left,
              previewTop: selectedBox.top,
              previewWidth: selectedBox.width,
              previewHeight: selectedBox.height,
            };
          } else if (hitSelectedBox(localX, localY)) {
            const geom = currentGeometry();
            const hitIndex = nearestBarIndexAtScreenX(localX, geom);
            boxSelect = {
              mode: 'move',
              offsetIndex: hitIndex - selectedBox.startIndex,
              offsetY: localY - selectedBox.top,
              spanBars: selectedBox.endIndex - selectedBox.startIndex,
              height: selectedBox.height,
              previewStartIndex: selectedBox.startIndex,
              previewEndIndex: selectedBox.endIndex,
              previewLeft: selectedBox.left,
              previewTop: selectedBox.top,
              previewWidth: selectedBox.width,
              previewHeight: selectedBox.height,
            };
          } else {
            selectedBox = null;
            const geom = currentGeometry();
            const startIndex = nearestBarIndexAtScreenX(localX, geom);
            boxSelect = {
              mode: 'new',
              startIndex,
              startY: localY,
            };
            const overlay = boxGeometryFromIndices(startIndex, startIndex, localY, 0, geom);
            boxSelect.previewStartIndex = startIndex;
            boxSelect.previewEndIndex = startIndex;
            boxSelect.previewLeft = overlay.left;
            boxSelect.previewTop = overlay.top;
            boxSelect.previewWidth = overlay.width;
            boxSelect.previewHeight = overlay.height;
            updateSelectionOverlay(
              overlay.left,
              overlay.top,
              overlay.width,
              overlay.height,
              selectionDragColor,
            );
          }
          event.preventDefault();
        });

        interactionLayer.addEventListener('mousemove', function(event) {
          if (toolMode !== 'select') {
            return;
          }
          const rect = getShellRect();
          const geom = currentGeometry();
          const localX = event.clientX - rect.left;
          const localY = event.clientY - rect.top;
          const snappedIndex = nearestBarIndexAtScreenX(localX, geom);
          const snappedX = indexToScreenX(snappedIndex, geom);
          showCrosshair(snappedIndex, Math.min(Math.max(localY, geom.top), geom.bottom), geom);
          const edge = hitSelectedBoxEdge(localX, localY);
          if (edge === 'left' || edge === 'right') {
            interactionLayer.style.cursor = 'ew-resize';
          } else if (edge === 'top' || edge === 'bottom') {
            interactionLayer.style.cursor = 'ns-resize';
          } else {
            interactionLayer.style.cursor = hitSelectedBox(localX, localY) ? 'move' : 'crosshair';
          }
        });
        interactionLayer.addEventListener('mouseleave', function() {
          hideCrosshair();
        });
      }

      window.addEventListener('mousemove', function(event) {
        if (boxSelect) {
          const rect = getShellRect();
          const geom = currentGeometry();
          const localX = Math.min(Math.max(event.clientX - rect.left, geom.left), geom.right);
          const localY = Math.min(Math.max(event.clientY - rect.top, geom.top), geom.bottom);
          const snappedIndex = nearestBarIndexAtScreenX(localX, geom);
          showCrosshair(snappedIndex, localY, geom);
          let left, top, width, height;
          let startIndex, endIndex;
          if (boxSelect.mode === 'move' && selectedBox) {
            const anchorIndex = nearestBarIndexAtScreenX(localX, geom);
            const maxStart = Math.max(0, bars.length - 1 - boxSelect.spanBars);
            startIndex = Math.min(Math.max(0, anchorIndex - boxSelect.offsetIndex), maxStart);
            endIndex = startIndex + boxSelect.spanBars;
            top = Math.min(Math.max(geom.top, localY - boxSelect.offsetY), geom.bottom - boxSelect.height);
            height = boxSelect.height;
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          } else if (boxSelect.mode === 'resize-left') {
            startIndex = Math.min(nearestBarIndexAtScreenX(localX, geom), boxSelect.endIndex);
            endIndex = boxSelect.endIndex;
            top = boxSelect.originalTop;
            height = boxSelect.originalHeight;
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          } else if (boxSelect.mode === 'resize-right') {
            startIndex = boxSelect.startIndex;
            endIndex = Math.max(nearestBarIndexAtScreenX(localX, geom), boxSelect.startIndex);
            top = boxSelect.originalTop;
            height = boxSelect.originalHeight;
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          } else if (boxSelect.mode === 'resize-top') {
            startIndex = boxSelect.startIndex;
            endIndex = boxSelect.endIndex;
            top = Math.min(localY, boxSelect.originalTop + boxSelect.originalHeight);
            height = Math.abs((boxSelect.originalTop + boxSelect.originalHeight) - localY);
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          } else if (boxSelect.mode === 'resize-bottom') {
            startIndex = boxSelect.startIndex;
            endIndex = boxSelect.endIndex;
            top = boxSelect.originalTop;
            height = Math.abs(localY - boxSelect.originalTop);
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          } else {
            const currentIndex = nearestBarIndexAtScreenX(localX, geom);
            startIndex = Math.min(boxSelect.startIndex, currentIndex);
            endIndex = Math.max(boxSelect.startIndex, currentIndex);
            top = Math.min(boxSelect.startY, localY);
            height = Math.abs(localY - boxSelect.startY);
            ({ left, width } = boxGeometryFromIndices(startIndex, endIndex, top, height, geom));
          }
          boxSelect.previewStartIndex = startIndex;
          boxSelect.previewEndIndex = endIndex;
          boxSelect.previewLeft = left;
          boxSelect.previewTop = top;
          boxSelect.previewWidth = width;
          boxSelect.previewHeight = height;
          updateSelectionOverlay(
            left,
            top,
            width,
            height,
            selectionDragColor,
          );
          updateSelectionSummary(startIndex, endIndex, top, top + height, geom, left, top, width);
          return;
        }
        if (!axisDrag) {
          return;
        }

        if (axisDrag.mode === 'xzoom') {
          const delta = event.clientX - axisDrag.startX;
          const span = axisDrag.right - axisDrag.left;
          const factor = Math.exp(delta / 240);
          const center = (axisDrag.left + axisDrag.right) / 2;
          const nextSpan = span * factor;
          relayoutXRange(center - (nextSpan / 2), center + (nextSpan / 2));
          return;
        }

        if (axisDrag.mode === 'yzoom') {
          const delta = event.clientY - axisDrag.startY;
          const span = axisDrag.top - axisDrag.bottom;
          const factor = Math.exp(delta / 180);
          const center = (axisDrag.top + axisDrag.bottom) / 2;
          const nextSpan = span * factor;
          relayoutYRange(center - (nextSpan / 2), center + (nextSpan / 2));
        }
      });

      window.addEventListener('mouseup', function(event) {
        if (boxSelect) {
          const geom = currentGeometry();
          const overlayLeft = Number(boxSelect.previewLeft || 0);
          const overlayTop = Number(boxSelect.previewTop || 0);
          const overlayWidth = Number(boxSelect.previewWidth || 0);
          const overlayHeight = Number(boxSelect.previewHeight || 0);
          selectedBox = {
            startIndex: boxSelect.previewStartIndex,
            endIndex: boxSelect.previewEndIndex,
            left: overlayLeft,
            top: overlayTop,
            width: overlayWidth,
            height: overlayHeight,
          };
          updateSelectionOverlay(
            selectedBox.left,
            selectedBox.top,
            selectedBox.width,
            selectedBox.height,
            selectionColorForRange(selectedBox.startIndex, selectedBox.endIndex),
          );
          updateSelectionSummary(selectedBox.startIndex, selectedBox.endIndex, overlayTop, overlayTop + overlayHeight, geom, selectedBox.left, selectedBox.top, selectedBox.width);
          syncInteractionLayer(true);
          boxSelect = null;
          return;
        }
        axisDrag = null;
      });

      if (panButton) {
        panButton.addEventListener('click', function() {
          setMode('pan');
        });
      }
      if (selectButton) {
        selectButton.addEventListener('click', function() {
          setMode('select');
        });
      }
      if (zoomButton) {
        zoomButton.addEventListener('click', function() {
          setMode('zoom');
        });
      }
      if (homeButton) {
        homeButton.addEventListener('click', function() {
          resetView();
        });
      }

      setActiveButton('pan');
      syncInteractionLayer(false);
      resetHoverReadout();
      updateAxisTicks(gd, initialLeft, initialRight);
      gd.on('plotly_hover', function(eventData) {
        const point = eventData && eventData.points
          ? eventData.points.find((item) => item.data && item.data.type === 'candlestick')
          : null;
        if (point) {
          updateHoverReadout(point);
        }
      });
      gd.on('plotly_unhover', function() {
        resetHoverReadout();
      });
      gd.on('plotly_relayout', function(eventData) {
        if (!eventData) {
          return;
        }
        const xRange = eventData['xaxis.range'] || (
          eventData['xaxis.range[0]'] !== undefined && eventData['xaxis.range[1]'] !== undefined
            ? [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']]
            : null
        );
        if (xRange) {
          updateAxisTicks(gd, Number(xRange[0]), Number(xRange[1]));
        }
      });
    })();
    """ % (
        json.dumps(
        [
            {
                "timestamp": _display_label(bar.timestamp),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
            }
            for bar in display_bars
        ]
        ),
        visible_start_index - 0.5,
        len(display_bars) - 0.5,
        initial_y_range[0],
        initial_y_range[1],
    )
    return to_html(
        figure,
        include_plotlyjs="inline",
        full_html=False,
        div_id="trade-report-chart",
        post_script=post_script,
        config={
            "responsive": True,
            "scrollZoom": False,
            "displaylogo": False,
            "displayModeBar": False,
        },
    )


def _render_equity_chart(result: BacktestResult, display_bars: list[MarketBar]) -> str:
    figure = go.Figure()
    timestamp_labels = [_display_label(bar.timestamp) for bar in display_bars]
    figure.add_trace(
        go.Scatter(
            x=[bar.timestamp for bar in display_bars],
            y=result.equity_curve,
            mode="lines",
            name="Equity",
            line={"color": "#38bdf8", "width": 2},
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.08)",
            customdata=timestamp_labels,
            hovertemplate="%{customdata}<br>Equity=%{y:.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_dark",
        height=220,
        margin={"l": 24, "r": 24, "t": 16, "b": 28},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30,34,48,0.6)",
        dragmode=False,
        hovermode="x",
        showlegend=False,
        font={"family": "Inter, -apple-system, sans-serif", "color": "#e2e8f0", "size": 11},
    )
    figure.update_yaxes(
        tickformat=".2f",
        ticks="outside",
        automargin=True,
        fixedrange=True,
        gridcolor="rgba(148, 163, 184, 0.08)",
    )
    figure.update_xaxes(
        showticklabels=True,
        type="date",
        ticks="outside",
        automargin=True,
        fixedrange=True,
        tickformat="%Y-%m-%d",
        gridcolor="rgba(148, 163, 184, 0.08)",
    )
    return to_html(
        figure,
        include_plotlyjs=False,
        full_html=False,
        div_id="trade-equity-chart",
        config={
            "responsive": True,
            "scrollZoom": False,
            "displaylogo": False,
            "displayModeBar": False,
        },
    )


def _display_timestamp(timestamp):
    return timestamp + timedelta(hours=DISPLAY_TIMEZONE_OFFSET_HOURS)


def _display_label(timestamp) -> str:
    return _display_timestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def _display_bar(bar: MarketBar) -> MarketBar:
    return MarketBar(
        timestamp=_display_timestamp(bar.timestamp),
        symbol=bar.symbol,
        timeframe=bar.timeframe,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
    )


def _data_quality_payload(report: DataQualityReport | None) -> dict[str, object] | None:
    if report is None:
        return None
    return {
        "symbol": report.symbol,
        "timeframe": report.timeframe,
        "bar_count": report.bar_count,
        "issues": [asdict(issue) for issue in report.issues],
    }


def _data_quality_list(report: DataQualityReport | None) -> str:
    if report is None:
        return "<li>No data quality report available</li>"
    items = [
        f"<li>Bars: {report.bar_count}</li>",
        f"<li>Normalized symbol/timeframe: {escape(report.symbol)} / {escape(report.timeframe)}</li>",
    ]
    if report.issues:
        items.extend(
            f"<li>{escape(issue.severity.upper())} {escape(issue.code)}: {escape(issue.message)}</li>"
            for issue in report.issues
        )
    else:
        items.append("<li>Valid data source. No blocking issues detected.</li>")
    return "".join(items)
