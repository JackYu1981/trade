from __future__ import annotations

from collections import deque

from trade.models import MarketBar


DEFAULT_MA_TIMEFRAMES = ("15m", "1h", "4h", "1d")
DEFAULT_MA_PERIODS = (20, 60, 240)


def moving_average(bars: list[MarketBar], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")

    window: deque[float] = deque()
    rolling_sum = 0.0
    values: list[float | None] = []

    for bar in bars:
        window.append(bar.close)
        rolling_sum += bar.close

        if len(window) > period:
            rolling_sum -= window.popleft()

        if len(window) == period:
            values.append(rolling_sum / period)
        else:
            values.append(None)

    return values


def compute_ma_series_by_period(
    bars: list[MarketBar],
    periods: list[int] | tuple[int, ...],
) -> dict[int, list[float | None]]:
    return {period: moving_average(bars, period) for period in periods}


def align_ma_series_to_base_timeframe(
    base_bars: list[MarketBar],
    timeframe_bars: list[MarketBar],
    ma_by_period: dict[int, list[float | None]],
) -> list[dict[int, float | None]]:
    aligned: list[dict[int, float | None]] = []
    tf_index = 0

    for base_bar in base_bars:
        while tf_index + 1 < len(timeframe_bars) and timeframe_bars[tf_index + 1].timestamp <= base_bar.timestamp:
            tf_index += 1

        if not timeframe_bars or timeframe_bars[tf_index].timestamp > base_bar.timestamp:
            aligned.append({period: None for period in ma_by_period})
            continue

        aligned.append(
            {
                period: ma_values[tf_index]
                for period, ma_values in ma_by_period.items()
            }
        )

    return aligned


def build_multi_timeframe_ma_context(
    base_bars: list[MarketBar],
    bars_by_timeframe: dict[str, list[MarketBar]],
    periods: list[int] | tuple[int, ...],
) -> list[dict[str, dict[int, float | None]]]:
    context_by_index = [
        {timeframe: {period: None for period in periods} for timeframe in bars_by_timeframe}
        for _ in base_bars
    ]

    for timeframe, timeframe_bars in bars_by_timeframe.items():
        ma_by_period = compute_ma_series_by_period(timeframe_bars, periods)
        aligned = align_ma_series_to_base_timeframe(base_bars, timeframe_bars, ma_by_period)
        for index, values in enumerate(aligned):
            context_by_index[index][timeframe] = values

    return context_by_index
