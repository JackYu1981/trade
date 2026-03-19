from __future__ import annotations

from trade.models import FishWindowConfig, LegCriteria, MarketBar, SwingPoint, TrendLeg


def find_swing_points(bars: list[MarketBar], window: int) -> list[SwingPoint]:
    if window <= 0:
        raise ValueError("window must be positive")
    if len(bars) < (window * 2) + 1:
        return []

    raw_points: list[SwingPoint] = []
    for index in range(window, len(bars) - window):
        current = bars[index]
        neighborhood = bars[index - window : index + window + 1]
        if current.high == max(bar.high for bar in neighborhood):
            raw_points.append(
                SwingPoint(
                    bar_index=index,
                    timestamp=current.timestamp,
                    price=current.high,
                    kind="high",
                )
            )
        if current.low == min(bar.low for bar in neighborhood):
            raw_points.append(
                SwingPoint(
                    bar_index=index,
                    timestamp=current.timestamp,
                    price=current.low,
                    kind="low",
                )
            )

    ordered = sorted(raw_points, key=lambda point: (point.bar_index, 0 if point.kind == "low" else 1))
    return _compress_same_kind_points(ordered)


def build_trend_legs(bars: list[MarketBar], criteria: LegCriteria) -> list[TrendLeg]:
    swing_points = find_swing_points(bars, criteria.swing_window)
    legs: list[TrendLeg] = []

    for left, right in zip(swing_points, swing_points[1:]):
        if left.kind == "low" and right.kind == "high":
            legs.append(_build_leg(left, right, "up", criteria))
        elif left.kind == "high" and right.kind == "low":
            legs.append(_build_leg(left, right, "down", criteria))

    return legs


def tradeable_legs(bars: list[MarketBar], criteria: LegCriteria) -> list[TrendLeg]:
    return [leg for leg in build_trend_legs(bars, criteria) if leg.is_tradeable]


def default_fish_window_config() -> FishWindowConfig:
    return FishWindowConfig(
        window_bars=200,
        min_move_points_by_timeframe={
            "15m": 65.0,
            "1h": 150.0,
            "1d": 200.0,
        },
        point_size=0.0001,
    )


def build_window_legs(
    bars: list[MarketBar],
    config: FishWindowConfig,
) -> list[TrendLeg]:
    if not bars:
        return []
    if config.window_bars <= 1:
        raise ValueError("window_bars must be greater than 1")

    timeframe = bars[0].timeframe
    min_move_points = config.min_move_points_by_timeframe.get(timeframe)
    if min_move_points is None:
        raise ValueError(f"No fish-window threshold configured for timeframe: {timeframe}")

    candidates: list[TrendLeg] = []
    start_index = 0
    last_start = len(bars) - config.window_bars
    while start_index <= last_start:
        window = bars[start_index : start_index + config.window_bars]
        low_offset, low_bar = min(enumerate(window), key=lambda item: item[1].low)
        high_offset, high_bar = max(enumerate(window), key=lambda item: item[1].high)

        if low_offset == high_offset:
            start_index += 1
            continue

        if low_offset < high_offset:
            leg = _build_window_leg(
                direction="up",
                start_index=start_index + low_offset,
                start_bar=low_bar,
                end_index=start_index + high_offset,
                end_bar=high_bar,
                min_move_points=min_move_points,
                point_size=config.point_size,
            )
        else:
            leg = _build_window_leg(
                direction="down",
                start_index=start_index + high_offset,
                start_bar=high_bar,
                end_index=start_index + low_offset,
                end_bar=low_bar,
                min_move_points=min_move_points,
                point_size=config.point_size,
            )

        if leg.is_tradeable:
            candidates.append(leg)
            start_index = leg.end_index + 1
        else:
            start_index += 1

    return _deduplicate_window_legs(candidates)


def _build_leg(start: SwingPoint, end: SwingPoint, direction: str, criteria: LegCriteria) -> TrendLeg:
    duration_bars = end.bar_index - start.bar_index
    move_price = abs(end.price - start.price)
    move_points = move_price / criteria.point_size if criteria.point_size else move_price
    duration_ok = duration_bars >= criteria.min_duration_bars
    if criteria.max_duration_bars is None:
        max_duration_ok = True
    else:
        max_duration_ok = duration_bars <= criteria.max_duration_bars
    is_tradeable = move_points >= criteria.min_move_points and duration_ok and max_duration_ok

    return TrendLeg(
        direction=direction,
        start_index=start.bar_index,
        start_time=start.timestamp,
        start_price=start.price,
        end_index=end.bar_index,
        end_time=end.timestamp,
        end_price=end.price,
        extreme_index=end.bar_index,
        extreme_time=end.timestamp,
        extreme_price=end.price,
        duration_bars=duration_bars,
        move_points=move_points,
        is_tradeable=is_tradeable,
    )


def _compress_same_kind_points(points: list[SwingPoint]) -> list[SwingPoint]:
    if not points:
        return []

    compressed: list[SwingPoint] = [points[0]]
    for point in points[1:]:
        previous = compressed[-1]
        if point.kind != previous.kind:
            compressed.append(point)
            continue

        if point.kind == "high" and point.price >= previous.price:
            compressed[-1] = point
        elif point.kind == "low" and point.price <= previous.price:
            compressed[-1] = point

    return compressed


def _build_window_leg(
    *,
    direction: str,
    start_index: int,
    start_bar: MarketBar,
    end_index: int,
    end_bar: MarketBar,
    min_move_points: float,
    point_size: float,
) -> TrendLeg:
    start_price = start_bar.low if direction == "up" else start_bar.high
    end_price = end_bar.high if direction == "up" else end_bar.low
    move_points = abs(end_price - start_price) / point_size if point_size else abs(end_price - start_price)
    return TrendLeg(
        direction=direction,
        start_index=start_index,
        start_time=start_bar.timestamp,
        start_price=start_price,
        end_index=end_index,
        end_time=end_bar.timestamp,
        end_price=end_price,
        extreme_index=end_index,
        extreme_time=end_bar.timestamp,
        extreme_price=end_price,
        duration_bars=end_index - start_index,
        move_points=move_points,
        is_tradeable=move_points >= min_move_points,
    )


def _deduplicate_window_legs(legs: list[TrendLeg]) -> list[TrendLeg]:
    deduped: list[TrendLeg] = []
    seen: set[tuple[str, int, int]] = set()
    for leg in legs:
        key = (leg.direction, leg.start_index, leg.end_index)
        if key in seen:
            continue
        deduped.append(leg)
        seen.add(key)
    return deduped
