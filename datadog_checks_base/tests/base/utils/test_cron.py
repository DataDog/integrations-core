# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from datadog_checks.base.utils.cron import CronExpression, CronScheduler


def utc_timestamp(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> float:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp()


def iso_format(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


@pytest.fixture
def daily_at_nine() -> CronScheduler:
    return CronScheduler("0 9 * * *")


# 2026-01-01 00:00:00 UTC is a Thursday, picked as the anchor for the tables below.
BASE_TIMESTAMP = utc_timestamp(2026, 1, 1)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expression",
    [
        "* * * * *",
        "0 0 * * *",
        "*/5 * * * *",
        "0 9 * * *",
        "15,45 * * * *",
        "0 0 1 1 *",
        "0 0 1 */3 *",
        "*/5 * * * 0",
        "* * * * 7",
        "0 0 29 2 *",
        "0 0 * * 1-5",
        "7-23/4 * * * *",
        "0 8-17/2 * * 1",
        "0 0 1,15 * *",
        "0,15,30,45 * * * *",
        "  0  9  *  *  *  ",
    ],
)
def test_cron_expression_accepts_valid(expression: str) -> None:
    assert CronExpression.is_valid(expression)
    CronExpression(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "   ",
        "* * * *",
        "* * * * * *",
        "60 * * * *",
        "* 24 * * *",
        "* * 0 * *",
        "* * 32 * *",
        "* * * 0 *",
        "* * * 13 *",
        "* * * * 8",
        "*/0 * * * *",
        "5-2 * * * *",
        "foo * * * *",
        "@daily",
        "@hourly",
        "@reboot",
        "JAN * * * *",
        "* * * * MON",
        "-1 * * * *",
        "1- * * * *",
        "-3 * * * *",
        "1,,3 * * * *",
        "*/-1 * * * *",
        "1/2 * * * */0",
        "10-5 * * * *",
    ],
)
def test_cron_expression_rejects_invalid(expression: str) -> None:
    assert not CronExpression.is_valid(expression)
    with pytest.raises(ValueError):
        CronExpression(expression)


@pytest.mark.parametrize("bad", [None, 123, 1.5, object(), [], {}])
def test_is_valid_returns_false_for_non_string(bad: object) -> None:
    assert not CronExpression.is_valid(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [None, 123, 1.5, object(), [], {}])
def test_cron_expression_raises_type_error_for_non_string(bad: object) -> None:
    with pytest.raises(TypeError):
        CronExpression(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "expression",
    [
        "0 0 31 2 *",
        "0 0 30 2 *",
        "0 0 31 4 *",
        "0 0 31 4,6,9,11 *",
    ],
)
def test_unsatisfiable_dom_month_combo_rejected_at_parse_time(expression: str) -> None:
    assert not CronExpression.is_valid(expression)
    with pytest.raises(ValueError):
        CronExpression(expression)


def test_unsatisfiable_combo_allowed_when_dow_provides_or_match() -> None:
    assert CronExpression.is_valid("0 0 31 2 1")


@pytest.mark.parametrize(
    "left_expression,right_expression",
    [
        ("0 0 * * 7", "0 0 * * 0"),
        ("0 0 * * 0,7", "0 0 * * 0"),
        ("0 0 * * 1-7", "0 0 * * 0-6"),
        ("5,5,1-6 * * * *", "1-6 * * * *"),
        ("* 4,1-4,5 * * *", "* 1-5 * * *"),
        ("* * * * 2-3,4-5,3", "* * * * 2-5"),
        ("0 0 1 1,1,3,3 *", "0 0 1 1,3 *"),
    ],
)
def test_semantically_equivalent_expressions_compare_equal(left_expression: str, right_expression: str) -> None:
    left = CronExpression(left_expression)
    right = CronExpression(right_expression)
    assert left == right
    assert hash(left) == hash(right)


# ---------------------------------------------------------------------------
# Tick math, table-driven; one table fuels next_tick and previous_tick.
# Each row is (expression, anchor, expected_next, expected_prev).
# ---------------------------------------------------------------------------


NEXT_PREV_CASES = [
    pytest.param(
        "* * * * *",
        BASE_TIMESTAMP,
        utc_timestamp(2026, 1, 1, 0, 1),
        utc_timestamp(2025, 12, 31, 23, 59),
        id="every-minute",
    ),
    pytest.param(
        "0 * * * *", BASE_TIMESTAMP, utc_timestamp(2026, 1, 1, 1), utc_timestamp(2025, 12, 31, 23), id="hourly"
    ),
    pytest.param(
        "0 9 * * *", BASE_TIMESTAMP, utc_timestamp(2026, 1, 1, 9), utc_timestamp(2025, 12, 31, 9), id="daily-at-9"
    ),
    pytest.param(
        "0 9 * * *",
        utc_timestamp(2026, 1, 1, 9),
        utc_timestamp(2026, 1, 2, 9),
        utc_timestamp(2025, 12, 31, 9),
        id="on-9-boundary",
    ),
    pytest.param(
        "0 9 * * *",
        utc_timestamp(2026, 1, 1, 9, 1),
        utc_timestamp(2026, 1, 2, 9),
        utc_timestamp(2026, 1, 1, 9),
        id="one-min-after-9",
    ),
    pytest.param(
        "*/5 * * * *",
        utc_timestamp(2026, 1, 1, 0, 3),
        utc_timestamp(2026, 1, 1, 0, 5),
        utc_timestamp(2026, 1, 1, 0, 0),
        id="every-5-mid",
    ),
    pytest.param(
        "0 9 * * 1", BASE_TIMESTAMP, utc_timestamp(2026, 1, 5, 9), utc_timestamp(2025, 12, 29, 9), id="weekly-monday-9"
    ),
    pytest.param(
        "0 0 1 1 *", BASE_TIMESTAMP, utc_timestamp(2027, 1, 1), utc_timestamp(2025, 1, 1), id="new-year-from-new-year"
    ),
    pytest.param(
        "0 0 29 2 *", utc_timestamp(2026, 3, 1), utc_timestamp(2028, 2, 29), utc_timestamp(2024, 2, 29), id="leap-day"
    ),
    pytest.param(
        "0 0 1 * *",
        utc_timestamp(2026, 1, 1, 12),
        utc_timestamp(2026, 2, 1),
        utc_timestamp(2026, 1, 1),
        id="monthly-first",
    ),
    pytest.param(
        "7-23/4 * * * *",
        BASE_TIMESTAMP,
        utc_timestamp(2026, 1, 1, 0, 7),
        utc_timestamp(2025, 12, 31, 23, 23),
        id="range-step-minutes",
    ),
    pytest.param(
        "0 0 1 */3 *", BASE_TIMESTAMP, utc_timestamp(2026, 4, 1), utc_timestamp(2025, 10, 1), id="quarterly-first"
    ),
    pytest.param(
        "0 0 1 * 1", BASE_TIMESTAMP, utc_timestamp(2026, 1, 5), utc_timestamp(2025, 12, 29), id="vixie-or-dom1-or-mon"
    ),
    pytest.param("0 0 * * 0", BASE_TIMESTAMP, utc_timestamp(2026, 1, 4), utc_timestamp(2025, 12, 28), id="sunday-as-0"),
    pytest.param("0 0 * * 7", BASE_TIMESTAMP, utc_timestamp(2026, 1, 4), utc_timestamp(2025, 12, 28), id="sunday-as-7"),
    pytest.param(
        "0 0 31 * *",
        utc_timestamp(2026, 3, 1),
        utc_timestamp(2026, 3, 31),
        utc_timestamp(2026, 1, 31),
        id="31st-skips-feb",
    ),
    pytest.param(
        "15,45 * * * *",
        BASE_TIMESTAMP,
        utc_timestamp(2026, 1, 1, 0, 15),
        utc_timestamp(2025, 12, 31, 23, 45),
        id="list-15-and-45",
    ),
    pytest.param(
        "* * * * *",
        utc_timestamp(2026, 1, 1) + 0.5,
        utc_timestamp(2026, 1, 1, 0, 1),
        utc_timestamp(2026, 1, 1, 0, 0),
        id="every-minute-fractional",
    ),
    pytest.param(
        "5/15 * * * *",
        BASE_TIMESTAMP,
        utc_timestamp(2026, 1, 1, 0, 5),
        utc_timestamp(2025, 12, 31, 23, 50),
        id="n-step-extends-to-high",
    ),
    pytest.param(
        "1/2 * * * *",
        BASE_TIMESTAMP,
        utc_timestamp(2026, 1, 1, 0, 1),
        utc_timestamp(2025, 12, 31, 23, 59),
        id="odd-minutes-via-n-step",
    ),
    pytest.param(
        "0 0 31 1 3",
        utc_timestamp(2026, 2, 15),
        utc_timestamp(2027, 1, 6),
        utc_timestamp(2026, 1, 31),
        id="vixie-or-with-month-boundary-cross",
    ),
    pytest.param(
        "0 16 */2 * 6",
        utc_timestamp(2023, 5, 2),
        utc_timestamp(2023, 5, 3, 16),
        utc_timestamp(2023, 5, 1, 16),
        id="vixie-or-stepped-dom-with-saturday",
    ),
    pytest.param(
        "5 0 */2 * *",
        utc_timestamp(2012, 2, 24),
        utc_timestamp(2012, 2, 25, 0, 5),
        utc_timestamp(2012, 2, 23, 0, 5),
        id="stepped-dom-previous-from-even-day",
    ),
    pytest.param(
        "0 0 22 * *",
        utc_timestamp(2012, 3, 15),
        utc_timestamp(2012, 3, 22),
        utc_timestamp(2012, 2, 22),
        id="dom-prev-crosses-into-previous-month",
    ),
    pytest.param(
        "0 0 * * 0,6",
        utc_timestamp(2010, 8, 25, 15, 56),
        utc_timestamp(2010, 8, 28),
        utc_timestamp(2010, 8, 22),
        id="weekend-dow-list-both-directions",
    ),
    pytest.param(
        "0 0 1 1,3,6,9,12 *",
        utc_timestamp(2026, 1, 15),
        utc_timestamp(2026, 3, 1),
        utc_timestamp(2026, 1, 1),
        id="quarterly-via-month-comma-list",
    ),
]


@pytest.mark.parametrize("expression,anchor,expected_next,_expected_prev", NEXT_PREV_CASES)
def test_next_tick(expression: str, anchor: float, expected_next: float, _expected_prev: float) -> None:
    got = CronExpression(expression).next_tick(after=anchor)
    assert got == expected_next, (
        f"{expression} from {iso_format(anchor)}: got {iso_format(got)}, expected {iso_format(expected_next)}"
    )


@pytest.mark.parametrize("expression,anchor,_expected_next,expected_prev", NEXT_PREV_CASES)
def test_previous_tick(expression: str, anchor: float, _expected_next: float, expected_prev: float) -> None:
    got = CronExpression(expression).previous_tick(before=anchor)
    assert got == expected_prev, (
        f"{expression} before {iso_format(anchor)}: got {iso_format(got)}, expected {iso_format(expected_prev)}"
    )


@pytest.mark.parametrize(
    "expression,count",
    [
        ("* * * * *", 60),
        ("*/5 * * * *", 12),
        ("0 9 * * *", 7),
        ("0 0 * * 1", 4),
        ("0 0 1 * *", 13),
    ],
)
def test_next_tick_is_strictly_monotone(expression: str, count: int) -> None:
    expr = CronExpression(expression)
    t = BASE_TIMESTAMP
    ticks = []
    for _ in range(count):
        t = expr.next_tick(after=t)
        ticks.append(t)
    assert ticks == sorted(set(ticks))


@pytest.mark.parametrize(
    "expression,anchor",
    [
        ("0 9 * * *", utc_timestamp(2026, 1, 1, 9, 0)),
        ("* * * * *", utc_timestamp(2026, 1, 1, 0, 0)),
        ("0 0 1 1 *", utc_timestamp(2026, 1, 1, 0, 0)),
    ],
)
def test_next_and_previous_are_strict_on_tick_boundary(expression: str, anchor: float) -> None:
    expr = CronExpression(expression)
    assert expr.next_tick(after=anchor) > anchor
    assert expr.previous_tick(before=anchor) < anchor


def test_cron_expression_equality_and_repr() -> None:
    a = CronExpression("0 9 * * *")
    b = CronExpression("  0   9  *  *  *  ")
    c = CronExpression("0 10 * * *")
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert a != "0 9 * * *"
    assert repr(a) == "CronExpression('0 9 * * *')"
    assert a.expression == "0 9 * * *"


# ---------------------------------------------------------------------------
# CronScheduler
# ---------------------------------------------------------------------------


def test_scheduler_constructor_accepts_string_and_expression() -> None:
    from_str = CronScheduler("0 9 * * *")
    from_expr = CronScheduler(CronExpression("0 9 * * *"))
    assert from_str.expression == from_expr.expression


@pytest.mark.parametrize("bad", [None, 42, 3.14, object()])
def test_scheduler_rejects_bad_expression_type(bad: object) -> None:
    with pytest.raises(TypeError):
        CronScheduler(bad)  # type: ignore[arg-type]


def test_scheduler_rejects_negative_lookback() -> None:
    with pytest.raises(ValueError):
        CronScheduler("* * * * *", startup_lookback=-1.0)


def test_scheduler_next_tick_none_before_first_call(daily_at_nine: CronScheduler) -> None:
    assert daily_at_nine.next_tick is None


def test_scheduler_fresh_no_ticks_due(daily_at_nine: CronScheduler) -> None:
    out = daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 30))
    assert out == []
    assert daily_at_nine.next_tick == utc_timestamp(2026, 1, 1, 9)


def test_scheduler_fires_after_tick_crossed(daily_at_nine: CronScheduler) -> None:
    daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 30))
    out = daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 9, 0))
    assert out == [utc_timestamp(2026, 1, 1, 9)]
    assert daily_at_nine.next_tick == utc_timestamp(2026, 1, 2, 9)


def test_scheduler_idempotent_within_same_polling_window(daily_at_nine: CronScheduler) -> None:
    daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 55))
    poll = utc_timestamp(2026, 1, 1, 9, 1)
    first = daily_at_nine.due_ticks(now=poll)
    second = daily_at_nine.due_ticks(now=poll)
    assert first == [utc_timestamp(2026, 1, 1, 9)]
    assert second == []


def test_scheduler_does_not_fire_past_tick_without_startup_lookback() -> None:
    s = CronScheduler("0 9 * * *")
    out = s.due_ticks(now=utc_timestamp(2026, 1, 1, 9, 30))
    assert out == []
    assert s.next_tick == utc_timestamp(2026, 1, 2, 9)


def test_scheduler_does_not_block(daily_at_nine: CronScheduler, monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda secs: sleep_calls.append(secs))
    for _ in range(20):
        daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 30))
    assert sleep_calls == []


def test_scheduler_yields_multiple_missed_ticks(daily_at_nine: CronScheduler) -> None:
    daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 30))
    out = daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 4, 12, 0))
    assert out == [
        utc_timestamp(2026, 1, 1, 9),
        utc_timestamp(2026, 1, 2, 9),
        utc_timestamp(2026, 1, 3, 9),
        utc_timestamp(2026, 1, 4, 9),
    ]
    assert daily_at_nine.next_tick == utc_timestamp(2026, 1, 5, 9)


def test_scheduler_advances_state_when_lookback_window_misses() -> None:
    s = CronScheduler("0 * * * *", startup_lookback=300)
    out = s.due_ticks(now=utc_timestamp(2026, 1, 1, 12, 30))
    assert out == []
    assert s.next_tick == utc_timestamp(2026, 1, 1, 13)


@pytest.mark.parametrize(
    "expression,lookback,now,expected",
    [
        pytest.param("0 * * * *", 0.0, utc_timestamp(2026, 1, 1, 12, 0), [], id="no-lookback"),
        pytest.param(
            "0 * * * *",
            7200,
            utc_timestamp(2026, 1, 1, 12, 3),
            [utc_timestamp(2026, 1, 1, 12, 0)],
            id="generous-window-catches-prev",
        ),
        pytest.param("0 * * * *", 300, utc_timestamp(2026, 1, 1, 12, 30), [], id="narrow-window-misses"),
        pytest.param(
            "*/10 * * * *",
            600,
            utc_timestamp(2026, 1, 1, 12, 3),
            [utc_timestamp(2026, 1, 1, 12, 0)],
            id="recent-tick-inside-window",
        ),
        pytest.param(
            "0 9 * * *",
            3600,
            utc_timestamp(2026, 1, 1, 9, 30),
            [utc_timestamp(2026, 1, 1, 9)],
            id="daily-startup-30min-after",
        ),
    ],
)
def test_scheduler_startup_lookback(expression: str, lookback: float, now: float, expected: list[float]) -> None:
    s = CronScheduler(expression, startup_lookback=lookback)
    assert s.due_ticks(now=now) == expected


def test_scheduler_default_now_uses_wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = utc_timestamp(2026, 1, 1, 8, 30)
    monkeypatch.setattr(time, "time", lambda: fixed)
    s = CronScheduler("0 9 * * *")
    assert s.due_ticks() == []
    assert s.next_tick == utc_timestamp(2026, 1, 1, 9)


def test_scheduler_due_ticks_returns_list(daily_at_nine: CronScheduler) -> None:
    result = daily_at_nine.due_ticks(now=utc_timestamp(2026, 1, 1, 8, 30))
    assert isinstance(result, list)


def test_scheduler_advances_correctly_across_ten_ticks() -> None:
    s = CronScheduler("0 * * * *")
    s.due_ticks(now=utc_timestamp(2026, 1, 1, 0, 30))
    collected: list[float] = []
    for hour in range(1, 11):
        collected.extend(s.due_ticks(now=utc_timestamp(2026, 1, 1, hour, 0)))
    assert collected == [utc_timestamp(2026, 1, 1, hour) for hour in range(1, 11)]
