from __future__ import annotations

from trade.models import MarketBar, RuleResult


def bullish_ma_stack(
    ma_values: dict[int, float | None],
    *,
    timeframe: str,
    fast_period: int,
    mid_period: int,
    slow_period: int,
) -> RuleResult:
    fast = ma_values.get(fast_period)
    mid = ma_values.get(mid_period)
    slow = ma_values.get(slow_period)
    if fast is None or mid is None or slow is None:
        return RuleResult(
            rule_id="trend.bullish_ma_stack",
            passed=False,
            phase="trend",
            reason_code="indicator_unavailable",
            message=(
                f"Trend stack blocked because {timeframe} MA{fast_period}/MA{mid_period}/MA{slow_period} "
                "is not fully available."
            ),
            metadata={"timeframe": timeframe, "periods": [fast_period, mid_period, slow_period]},
        )

    passed = fast > mid > slow
    return RuleResult(
        rule_id="trend.bullish_ma_stack",
        passed=passed,
        phase="trend",
        reason_code="bullish_stack" if passed else "stack_not_bullish",
        message=(
            f"{timeframe} MA stack is bullish."
            if passed
            else f"{timeframe} MA stack is not bullish."
        ),
        metadata={
            "timeframe": timeframe,
            "fast_period": fast_period,
            "mid_period": mid_period,
            "slow_period": slow_period,
            "fast_ma": fast,
            "mid_ma": mid,
            "slow_ma": slow,
        },
    )


def bearish_ma_stack(
    ma_values: dict[int, float | None],
    *,
    timeframe: str,
    fast_period: int,
    mid_period: int,
    slow_period: int,
) -> RuleResult:
    fast = ma_values.get(fast_period)
    mid = ma_values.get(mid_period)
    slow = ma_values.get(slow_period)
    if fast is None or mid is None or slow is None:
        return RuleResult(
            rule_id="trend.bearish_ma_stack",
            passed=False,
            phase="trend",
            reason_code="indicator_unavailable",
            message=(
                f"Trend stack blocked because {timeframe} MA{fast_period}/MA{mid_period}/MA{slow_period} "
                "is not fully available."
            ),
            metadata={"timeframe": timeframe, "periods": [fast_period, mid_period, slow_period]},
        )

    passed = fast < mid < slow
    return RuleResult(
        rule_id="trend.bearish_ma_stack",
        passed=passed,
        phase="trend",
        reason_code="bearish_stack" if passed else "stack_not_bearish",
        message=(
            f"{timeframe} MA stack is bearish."
            if passed
            else f"{timeframe} MA stack is not bearish."
        ),
        metadata={
            "timeframe": timeframe,
            "fast_period": fast_period,
            "mid_period": mid_period,
            "slow_period": slow_period,
            "fast_ma": fast,
            "mid_ma": mid,
            "slow_ma": slow,
        },
    )


def ma_pair_order(
    ma_values: dict[int, float | None],
    *,
    timeframe: str,
    left_period: int,
    right_period: int,
    relation: str,
    rule_id: str,
    positive_reason_code: str,
    negative_reason_code: str,
) -> RuleResult:
    left = ma_values.get(left_period)
    right = ma_values.get(right_period)
    if left is None or right is None:
        return RuleResult(
            rule_id=rule_id,
            passed=False,
            phase="trend",
            reason_code="indicator_unavailable",
            message=f"MA order blocked because {timeframe} MA{left_period} or MA{right_period} is unavailable.",
            metadata={"timeframe": timeframe, "left_period": left_period, "right_period": right_period},
        )

    if relation == "above":
        passed = left > right
        message = (
            f"{timeframe} MA{left_period} is above MA{right_period}."
            if passed
            else f"{timeframe} MA{left_period} is not above MA{right_period}."
        )
    elif relation == "below":
        passed = left < right
        message = (
            f"{timeframe} MA{left_period} is below MA{right_period}."
            if passed
            else f"{timeframe} MA{left_period} is not below MA{right_period}."
        )
    else:
        raise ValueError(f"Unsupported relation: {relation}")

    return RuleResult(
        rule_id=rule_id,
        passed=passed,
        phase="trend",
        reason_code=positive_reason_code if passed else negative_reason_code,
        message=message,
        metadata={
            "timeframe": timeframe,
            "left_period": left_period,
            "right_period": right_period,
            "left_ma": left,
            "right_ma": right,
            "relation": relation,
        },
    )


def trend_above_ma(bar: MarketBar, ma_value: float | None, *, timeframe: str, period: int) -> RuleResult:
    if ma_value is None:
        return RuleResult(
            rule_id="trend.above_ma",
            passed=False,
            phase="trend",
            reason_code="indicator_unavailable",
            message=f"Trend filter blocked because {timeframe} MA{period} is not available yet.",
        )

    passed = bar.close > ma_value
    return RuleResult(
        rule_id="trend.above_ma",
        passed=passed,
        phase="trend",
        reason_code="trend_up" if passed else "trend_down",
        message=(
            f"Close {bar.close:.5f} is {'above' if passed else 'at_or_below'} "
            f"{timeframe} MA{period} {ma_value:.5f}."
        ),
        metadata={"close": bar.close, "ma": ma_value, "timeframe": timeframe, "period": period},
    )


def trend_below_ma(bar: MarketBar, ma_value: float | None, *, timeframe: str, period: int) -> RuleResult:
    if ma_value is None:
        return RuleResult(
            rule_id="trend.below_ma",
            passed=False,
            phase="trend",
            reason_code="indicator_unavailable",
            message=f"Trend filter blocked because {timeframe} MA{period} is not available yet.",
        )

    passed = bar.close < ma_value
    return RuleResult(
        rule_id="trend.below_ma",
        passed=passed,
        phase="trend",
        reason_code="trend_down" if passed else "trend_up",
        message=(
            f"Close {bar.close:.5f} is {'below' if passed else 'at_or_above'} "
            f"{timeframe} MA{period} {ma_value:.5f}."
        ),
        metadata={"close": bar.close, "ma": ma_value, "timeframe": timeframe, "period": period},
    )


def entry_cross_above_ma(
    previous_bar: MarketBar | None,
    previous_ma: float | None,
    current_bar: MarketBar,
    current_ma: float | None,
    *,
    timeframe: str,
    period: int,
) -> RuleResult:
    if previous_bar is None or previous_ma is None or current_ma is None:
        return RuleResult(
            rule_id="entry.cross_above_ma",
            passed=False,
            phase="entry",
            reason_code="indicator_unavailable",
            message=f"Entry rule blocked because prior or current {timeframe} MA{period} is unavailable.",
        )

    crossed = previous_bar.close <= previous_ma and current_bar.close > current_ma
    return RuleResult(
        rule_id="entry.cross_above_ma",
        passed=crossed,
        phase="entry",
        reason_code="crossed_above" if crossed else "no_cross",
        message=(
            f"Detected bullish close/{timeframe} MA{period} cross."
            if crossed
            else f"No bullish close/{timeframe} MA{period} cross detected."
        ),
        metadata={
            "previous_close": previous_bar.close,
            "previous_ma": previous_ma,
            "current_close": current_bar.close,
            "current_ma": current_ma,
            "timeframe": timeframe,
            "period": period,
        },
    )


def exit_close_above_ma(bar: MarketBar, ma_value: float | None, *, timeframe: str, period: int) -> RuleResult:
    if ma_value is None:
        return RuleResult(
            rule_id="exit.close_above_ma",
            passed=False,
            phase="exit",
            reason_code="indicator_unavailable",
            message=f"Exit rule blocked because {timeframe} MA{period} is not available yet.",
        )

    passed = bar.close > ma_value
    return RuleResult(
        rule_id="exit.close_above_ma",
        passed=passed,
        phase="exit",
        reason_code="exit_signal" if passed else "hold_position",
        message=(
            f"Close rose above {timeframe} MA{period}."
            if passed
            else f"Close remains below or equal to {timeframe} MA{period}."
        ),
        metadata={"close": bar.close, "ma": ma_value, "timeframe": timeframe, "period": period},
    )


def exit_close_below_ma(bar: MarketBar, ma_value: float | None, *, timeframe: str, period: int) -> RuleResult:
    if ma_value is None:
        return RuleResult(
            rule_id="exit.close_below_ma",
            passed=False,
            phase="exit",
            reason_code="indicator_unavailable",
            message=f"Exit rule blocked because {timeframe} MA{period} is not available yet.",
        )

    passed = bar.close < ma_value
    return RuleResult(
        rule_id="exit.close_below_ma",
        passed=passed,
        phase="exit",
        reason_code="exit_signal" if passed else "hold_position",
        message=(
            f"Close fell below {timeframe} MA{period}."
            if passed
            else f"Close remains above or equal to {timeframe} MA{period}."
        ),
        metadata={"close": bar.close, "ma": ma_value, "timeframe": timeframe, "period": period},
    )
