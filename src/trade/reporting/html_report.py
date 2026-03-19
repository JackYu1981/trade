from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from html import escape
import json

from plotly import graph_objects as go
from plotly.io import to_html
from trade.analysis.baseline import build_window_legs, default_fish_window_config
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
        "data_quality": _data_quality_payload(data_quality_report),
        "trades": [asdict(trade) for trade in result.trades],
    }
    summary_cards = [
        ("Net PnL", f"{float(summary['net_pnl']):.5f}"),
        ("Total Return", f"{float(summary['total_return_pct']):.2%}"),
        ("Max Drawdown", f"{float(summary['max_drawdown']):.2%}"),
        ("Sharpe", f"{float(summary['sharpe']):.2f}"),
        ("Trades", str(summary["trade_count"])),
        ("Win Rate", f"{float(summary['win_rate']):.2%}"),
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
      --bg: #f4efe6;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d6d3d1;
      --accent: #0f766e;
      --positive: #166534;
      --negative: #b91c1c;
      --shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.08), transparent 28%),
        linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
    }}
    main {{
      width: min(1280px, calc(100vw - 32px));
      margin: 32px auto 64px;
      display: grid;
      gap: 20px;
    }}
    .hero, .panel {{
      background: var(--panel);
      border: 1px solid rgba(214, 211, 209, 0.85);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero {{
      padding: 28px;
      display: grid;
      gap: 14px;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      color: var(--accent);
    }}
    h1, h2 {{
      margin: 0;
      font-weight: 600;
    }}
    .subtle {{
      color: var(--muted);
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
    }}
    .card {{
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.78);
    }}
    .label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .value {{
      margin-top: 6px;
      font-size: 26px;
      font-weight: 600;
    }}
    .panel {{
      padding: 22px;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 20px;
    }}
    .chart-shell {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,244,236,0.92));
      overflow: hidden;
      position: relative;
    }}
    .equity-shell {{
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,244,236,0.92));
      overflow: hidden;
      position: relative;
    }}
    .chart-toolbar {{
      position: absolute;
      top: 18px;
      right: 18px;
      display: flex;
      gap: 6px;
      z-index: 3;
      padding: 6px;
      border: 1px solid rgba(214, 211, 209, 0.95);
      border-radius: 14px;
      background: rgba(255, 253, 248, 0.92);
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10);
      backdrop-filter: blur(8px);
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
      color: #1d4ed8;
      text-shadow: 0 1px 0 rgba(255, 255, 255, 0.9);
      font-size: 12px;
      line-height: 1.28;
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
    }}
    .chart-hover-readout .hover-values span {{
      min-width: 86px;
    }}
    .chart-tool {{
      width: 36px;
      height: 36px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: transparent;
      color: var(--ink);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
    }}
    .chart-tool:hover {{
      background: rgba(15, 118, 110, 0.08);
      border-color: rgba(15, 118, 110, 0.18);
    }}
    .chart-tool.active {{
      background: var(--accent);
      color: white;
      border-color: rgba(15, 118, 110, 0.4);
    }}
    .chart-analysis-box {{
      position: absolute;
      min-width: 180px;
      max-width: 240px;
      z-index: 3;
      padding: 12px 14px;
      border: 1px solid rgba(214, 211, 209, 0.95);
      border-radius: 14px;
      background: rgba(255, 253, 248, 0.96);
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.10);
      backdrop-filter: blur(8px);
      display: none;
    }}
    .chart-analysis-box strong {{
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
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
        rgba(15, 118, 110, 0.95) 0 8px,
        transparent 8px 14px
      ));
    }}
    .chart-selection-line.horizontal {{
      height: 1px;
      background-image: var(--selection-horizontal-stroke, repeating-linear-gradient(
        to right,
        rgba(15, 118, 110, 0.95) 0 8px,
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
        rgba(37, 99, 235, 0.65) 0 9px,
        transparent 9px 15px
      );
    }}
    .chart-crosshair-line.y {{
      width: 1px;
      background-image: repeating-linear-gradient(
        to bottom,
        rgba(37, 99, 235, 0.65) 0 9px,
        transparent 9px 15px
      );
    }}
    .chart-axis-label {{
      position: absolute;
      z-index: 3;
      pointer-events: none;
      display: none;
      padding: 2px 6px;
      border-radius: 8px;
      background: rgba(255, 253, 248, 0.96);
      border: 1px solid rgba(37, 99, 235, 0.22);
      color: #1d4ed8;
      font-size: 11px;
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
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
    }}
    th {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.45;
      color: #334155;
    }}
    .positive {{ color: var(--positive); }}
    .negative {{ color: var(--negative); }}
    @media (max-width: 900px) {{
      .split {{
        grid-template-columns: 1fr;
      }}
      main {{
        width: min(100vw - 20px, 1280px);
        margin-top: 20px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">Research Report</div>
      <h1>{escape(_strategy_display_name(str(summary['strategy_id'])))}</h1>
      <div class="subtle">{escape(str(summary['symbol']))} · {escape(str(summary['timeframe']))} · demo strategy used to validate report readability</div>
      <div class="grid">
        {"".join(f'<div class="card"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>' for label, value in summary_cards)}
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
        <div class="eyebrow">Review</div>
        <h2>Strategy Notes</h2>
        <ul>{suggestions_html}</ul>
        <div class="eyebrow" style="margin-top:18px;">Blocked Reasons</div>
        <ul>{blocked_html}</ul>
      </div>
      <div>
        <div class="eyebrow">Data Quality</div>
        <h2>Input Status</h2>
        <ul>{data_quality_html}</ul>
      </div>
    </section>

    <section class="panel">
      <div class="eyebrow">Trades</div>
      <h2>Execution Log</h2>
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
    </section>

    <section class="panel">
      <div class="eyebrow">Payload</div>
      <h2>Structured Snapshot</h2>
      <pre>{json_payload}</pre>
    </section>
  </main>
</body>
</html>
"""


def _render_plotly_chart(result: BacktestResult, bars: list[MarketBar], display_bars: list[MarketBar]) -> str:
    fish_legs = build_window_legs(bars, default_fish_window_config())
    ma60_values = moving_average(bars, period=60)
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
            increasing_line_color="#166534",
            decreasing_line_color="#b91c1c",
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

    if result.trades:
        entry_indices = [original_index_by_timestamp[trade.entry_time.isoformat()] for trade in result.trades]
        exit_indices = [original_index_by_timestamp[trade.exit_time.isoformat()] for trade in result.trades]
        figure.add_trace(
            go.Scatter(
                x=entry_indices,
                y=[trade.entry_price for trade in result.trades],
                mode="markers",
                name="Entries",
                marker={"size": 10, "color": "#0f766e", "symbol": "triangle-up"},
                customdata=[timestamp_labels[index] for index in entry_indices],
                hovertemplate="Entry<br>%{customdata}<br>Price=%{y:.5f}<extra></extra>",
            ),
        )
        figure.add_trace(
            go.Scatter(
                x=exit_indices,
                y=[trade.exit_price for trade in result.trades],
                mode="markers",
                name="Exits",
                marker={"size": 10, "color": "#b91c1c", "symbol": "triangle-down"},
                customdata=[timestamp_labels[index] for index in exit_indices],
                hovertemplate="Exit<br>%{customdata}<br>Price=%{y:.5f}<extra></extra>",
            ),
        )

    figure.add_trace(
        go.Scatter(
            x=bar_indices,
            y=ma60_values,
            mode="lines",
            name="MA60",
            line={"color": "#facc15", "width": 2},
            hoverinfo="skip",
        ),
    )

    figure.update_layout(
        template="plotly_white",
        height=820,
        margin={"l": 24, "r": 24, "t": 58, "b": 24},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
        dragmode="pan",
        hovermode="x",
        font={"family": "Georgia, Times New Roman, serif", "color": "#1f2937"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1},
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
        spikecolor="rgba(37, 99, 235, 0.65)",
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
        spikecolor="rgba(37, 99, 235, 0.65)",
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
        hoverReadout.style.color = closeValue >= openValue ? '#166534' : '#b91c1c';
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

      function updateSelectionSummary(startIndex, endIndex, startY, endY, geom) {
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
        showSelectionSummary(selectedBox.left, selectedBox.top, selectedBox.width);
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
          updateSelectionSummary(selectedBox.startIndex, selectedBox.endIndex, overlayTop, overlayTop + overlayHeight, geom);
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
            line={"color": "#2563eb", "width": 2},
            customdata=timestamp_labels,
            hovertemplate="%{customdata}<br>Equity=%{y:.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        template="plotly_white",
        height=220,
        margin={"l": 24, "r": 24, "t": 16, "b": 28},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
        dragmode=False,
        hovermode="x",
        showlegend=False,
        font={"family": "Georgia, Times New Roman, serif", "color": "#1f2937"},
    )
    figure.update_yaxes(
        tickformat=".2f",
        ticks="outside",
        automargin=True,
        fixedrange=True,
    )
    figure.update_xaxes(
        showticklabels=True,
        type="date",
        ticks="outside",
        automargin=True,
        fixedrange=True,
        tickformat="%Y-%m-%d",
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
