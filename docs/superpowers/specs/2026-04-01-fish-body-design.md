# Fish Body Identification — Design Spec

## Date
2026-04-01

## Context

The trade framework includes a baseline analysis module (`analysis/baseline.py`) that identifies "fish" — tradeable trend legs in historical market data. A fish represents a significant directional price move within a fixed-bar window.

The user's trading philosophy is to capture the **fish body** (鱼身): the most reliable, high-certainty segment of a trend. The head and tail of a fish represent volatile, uncertain startup and exhaustion phases that are difficult to trade profitably.

## Problem

Current `build_window_legs` finds whole fish (window-low to window-high) but does not identify the body. There is no mechanism to:
- Detect swing structure within a fish
- Isolate the highest-momentum segment
- Quantify how much of the body a strategy actually captured

## Fish Body Definition

Given a fish (a `TrendLeg` from `build_window_legs`):

1. Extract the bars within the fish's range (`start_index` to `end_index`)
2. Find swing high/low points within those bars using a configurable window parameter
3. For an "up" fish: from the swing sequence, take adjacent low→high pairs; the pair with the **largest move** (in points) is the body
4. For a "down" fish: take adjacent high→low pairs; the pair with the largest move is the body
5. The fish's start is guaranteed to be the extreme (lowest low for up, highest high for down) because `build_window_legs` selects the min-low/max-high bar within the window, so no internal swing point can break the overall direction

## Data Model Changes

Extend `TrendLeg` in `models.py` with optional body fields (default `None`):

```python
body_start_index: int | None = None
body_start_time: datetime | None = None
body_start_price: float | None = None
body_end_index: int | None = None
body_end_time: datetime | None = None
body_end_price: float | None = None
body_move_points: float | None = None
```

`None` means body was not computed (e.g. swing-leg method, or insufficient swing points inside the fish).

## Algorithm: `identify_fish_body`

Signature: `identify_fish_body(bars: list[MarketBar], leg: TrendLeg, swing_window: int, point_size: float) -> TrendLeg`

The function creates a **new** `TrendLeg` via `dataclasses.replace()` (since `TrendLeg` is frozen) with body fields populated.

```
function identify_fish_body(bars, leg, swing_window, point_size):
    fish_bars = bars[leg.start_index : leg.end_index + 1]
    swings = find_swing_points(fish_bars, window=swing_window)

    if fewer than 2 swings:
        return leg unchanged (body fields stay None)

    offset = leg.start_index   # convert slice-relative indices to absolute
    best_move = 0
    best_start = None
    best_end = None

    for each adjacent pair (left, right) in swings:
        if leg.direction == "up" and left.kind == "low" and right.kind == "high":
            move = (right.price - left.price) / point_size
            if move > best_move:
                best_move, best_start, best_end = move, left, right
        if leg.direction == "down" and left.kind == "high" and right.kind == "low":
            move = (left.price - right.price) / point_size
            if move > best_move:
                best_move, best_start, best_end = move, left, right

    if best_start is None:
        return leg unchanged

    return dataclasses.replace(leg,
        body_start_index = best_start.bar_index + offset,
        body_start_time  = fish_bars[best_start.bar_index].timestamp,
        body_start_price = best_start.price,
        body_end_index   = best_end.bar_index + offset,
        body_end_time    = fish_bars[best_end.bar_index].timestamp,
        body_end_price   = best_end.price,
        body_move_points = best_move,
    )
```

Tie-breaking: when two swing pairs have equal move size, the first (earlier) pair wins.

## Integration with `build_window_legs`

Add optional parameter `body_swing_window: int | None = None`:
- If `None`: behavior unchanged, body fields stay `None`
- If set: call `identify_fish_body(bars, leg, body_swing_window, config.point_size)` for each tradeable leg

The `point_size` is sourced from the existing `FishWindowConfig.point_size`.

## HTML Report Changes

In `_render_plotly_chart`, after drawing the existing light-colored vrect for each fish:
- If `leg.body_start_index is not None`, draw an additional vrect over the body range
- Up fish body: darker green (`rgba(0, 128, 0, 0.25)`)
- Down fish body: darker red (`rgba(178, 34, 34, 0.25)`)

This layers on top of the existing fish background for clear visual distinction.

## Optimal Window Discovery

After implementation, run `build_window_legs` with `body_swing_window` values 2 through 10 on real EUR/USD data (`examples/eurusd_1h_730d_yf.csv` and `examples/eurusd_15m_60d_yf.csv`). Select the window that maximizes the average `body_move_points` across all detected fish. This becomes the default value in `default_fish_window_config` or a new companion default.

## Test Plan

1. **Monotonic up fish**: All bars ascending — body should span the largest swing pair (may cover most of the fish)
2. **Internal wave fish**: Fish with clear internal oscillation — body should be the segment with max same-direction swing move
3. **Insufficient swings**: Fish too short or window too large for swing detection — body fields should be `None`
4. **Body equals entire fish**: Degenerate case where the single largest swing pair spans the whole fish
5. **Down fish body**: Verify body identification works correctly for downward fish
6. **Equal-move tie-breaking**: When two swing pairs have the same move, the earlier pair is selected
7. **`body_swing_window=None` passthrough**: Omitting the parameter leaves all body fields as `None`
8. **Existing tests unchanged**: All existing tests must continue to pass

## Out of Scope

- Modifying `build_trend_legs` (swing-leg method) — no body identification there
- Changing `FishWindowConfig` — window config for fish detection stays the same
- JSON/text report changes — deferred to next phase
- Strategy-vs-body alignment metrics — deferred to next phase
