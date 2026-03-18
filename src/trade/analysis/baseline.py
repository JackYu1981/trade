from __future__ import annotations

from trade.models import LegCriteria, MarketBar, SwingPoint, TrendLeg


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
