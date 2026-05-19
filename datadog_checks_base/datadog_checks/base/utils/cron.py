# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Standard 5-field UTC cron expression parsing and scheduling.

This module exists so integrations that want cron-style firing inside their
``check()`` method don't have to pull in a third-party cron library. Two
classes are exposed:

* ``CronExpression`` is the stateless tick calculator. Parse once, then ask
  for the next/previous tick relative to any timestamp.
* ``CronScheduler`` wraps an expression with the "is this tick mine to fire
  yet?" state machine that fits the per-``check()`` invocation pattern.

Only the standard 5-field syntax (minute hour day-of-month month day-of-week)
in UTC is supported. ``@``-aliases, seconds, year, month/day name aliases,
and ``L``/``W``/``#`` extensions are intentionally rejected.
"""

from __future__ import annotations

import time
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Iterator

UTC = timezone.utc

MINUTE_RANGE = (0, 59)
HOUR_RANGE = (0, 23)
DOM_RANGE = (1, 31)
MONTH_RANGE = (1, 12)
DOW_RANGE = (0, 7)

WALK_ITERATION_BUDGET = 366 * 8


def _parse_field(field: str, low: int, high: int) -> tuple[tuple[int, ...], bool]:
    """Parse one cron field into (sorted_unique_values, is_restricted)."""
    if not field:
        raise ValueError("empty cron field")

    is_restricted = field != "*"
    values: set[int] = set()

    for chunk in field.split(","):
        if not chunk:
            raise ValueError(f"empty value in cron field: {field!r}")

        base = chunk
        step = 1
        if "/" in chunk:
            base, _, step_str = chunk.partition("/")
            if not base or not step_str:
                raise ValueError(f"malformed step expression: {chunk!r}")
            try:
                step = int(step_str)
            except ValueError as exc:
                raise ValueError(f"step must be an integer: {chunk!r}") from exc
            if step <= 0:
                raise ValueError(f"step must be positive: {chunk!r}")

        if base == "*":
            start, end = low, high
        elif "-" in base:
            left, _, right = base.partition("-")
            if not left or not right:
                raise ValueError(f"malformed range: {base!r}")
            try:
                start, end = int(left), int(right)
            except ValueError as exc:
                raise ValueError(f"range bounds must be integers: {base!r}") from exc
            if start > end:
                raise ValueError(f"range start must be <= end: {base!r}")
        else:
            try:
                start = int(base)
            except ValueError as exc:
                raise ValueError(f"value must be an integer: {base!r}") from exc
            end = start

        if start < low or end > high:
            raise ValueError(f"value out of range [{low}, {high}] in {chunk!r}")

        values.update(range(start, end + 1, step))

    if not values:
        raise ValueError(f"cron field expanded to empty set: {field!r}")

    return tuple(sorted(values)), is_restricted


class CronExpression:
    """A parsed standard 5-field cron expression evaluated in UTC."""

    __slots__ = (
        "_dom_restricted",
        "_doms",
        "_dow_restricted",
        "_dows",
        "_expression",
        "_hours",
        "_minutes",
        "_months",
    )

    def __init__(self, expression: str) -> None:
        if not isinstance(expression, str):
            raise ValueError("cron expression must be a string")

        stripped = expression.strip()
        if not stripped:
            raise ValueError("cron expression is empty")
        if stripped.startswith("@"):
            raise ValueError(f"shortcut expressions are not supported: {expression!r}")

        fields = stripped.split()
        if len(fields) != 5:
            raise ValueError(f"expected 5 cron fields, got {len(fields)}: {expression!r}")

        minute_field, hour_field, dom_field, month_field, dow_field = fields

        self._minutes, _ = _parse_field(minute_field, *MINUTE_RANGE)
        self._hours, _ = _parse_field(hour_field, *HOUR_RANGE)
        self._doms, self._dom_restricted = _parse_field(dom_field, *DOM_RANGE)
        self._months, _ = _parse_field(month_field, *MONTH_RANGE)
        raw_dows, self._dow_restricted = _parse_field(dow_field, *DOW_RANGE)
        self._dows = tuple(sorted({0 if v == 7 else v for v in raw_dows}))
        self._expression = " ".join(fields)

    def __repr__(self) -> str:
        return f"CronExpression({self._expression!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CronExpression):
            return NotImplemented
        return self._expression == other._expression

    def __hash__(self) -> int:
        return hash(self._expression)

    @property
    def expression(self) -> str:
        """The normalized cron expression string."""
        return self._expression

    @classmethod
    def is_valid(cls, expression: str) -> bool:
        """Whether the given string parses as a supported cron expression."""
        try:
            cls(expression)
        except (ValueError, TypeError):
            return False
        return True

    def next_tick(self, after: float) -> float:
        """First scheduled tick strictly greater than ``after`` (epoch seconds, UTC)."""
        start = datetime.fromtimestamp(after, UTC).replace(second=0, microsecond=0) + timedelta(minutes=1)
        return self._walk(start, forward=True)

    def previous_tick(self, before: float) -> float:
        """Greatest scheduled tick strictly less than ``before`` (epoch seconds, UTC)."""
        ts = datetime.fromtimestamp(before, UTC)
        start = ts.replace(second=0, microsecond=0)
        if ts.second == 0 and ts.microsecond == 0:
            start = start - timedelta(minutes=1)
        return self._walk(start, forward=False)

    def _day_matches(self, year: int, month: int, day: int) -> bool:
        dom_match = day in self._doms
        cron_weekday = (datetime(year, month, day, tzinfo=UTC).weekday() + 1) % 7
        dow_match = cron_weekday in self._dows

        if self._dom_restricted and self._dow_restricted:
            return dom_match or dow_match
        if self._dom_restricted:
            return dom_match
        if self._dow_restricted:
            return dow_match
        return True

    def _walk(self, dt: datetime, *, forward: bool) -> float:
        for _ in range(WALK_ITERATION_BUDGET):
            if dt.month not in self._months:
                dt = self._jump_month(dt, forward)
                continue
            if not self._day_matches(dt.year, dt.month, dt.day):
                dt = self._jump_day(dt, forward)
                continue
            if dt.hour not in self._hours:
                dt = self._jump_hour(dt, forward)
                continue
            if dt.minute not in self._minutes:
                dt = self._jump_minute(dt, forward)
                continue
            return dt.timestamp()
        raise RuntimeError(
            f"cron expression {self._expression!r} has no matching tick within {WALK_ITERATION_BUDGET} steps; "
            "likely impossible (for example day 31 in a 30-day-only month)"
        )

    def _jump_month(self, dt: datetime, forward: bool) -> datetime:
        year, month = dt.year, dt.month
        if forward:
            year, month = self._roll_month(year, month + 1, forward)
            while month not in self._months:
                year, month = self._roll_month(year, month + 1, forward)
            return datetime(year, month, 1, 0, 0, tzinfo=UTC)

        year, month = self._roll_month(year, month - 1, forward)
        while month not in self._months:
            year, month = self._roll_month(year, month - 1, forward)
        return datetime(year, month, monthrange(year, month)[1], 23, 59, tzinfo=UTC)

    @staticmethod
    def _roll_month(year: int, month: int, forward: bool) -> tuple[int, int]:
        if forward and month > 12:
            return year + 1, 1
        if not forward and month < 1:
            return year - 1, 12
        return year, month

    @staticmethod
    def _jump_day(dt: datetime, forward: bool) -> datetime:
        if forward:
            return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return (dt - timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)

    def _jump_hour(self, dt: datetime, forward: bool) -> datetime:
        if forward:
            for hour in self._hours:
                if hour > dt.hour:
                    return dt.replace(hour=hour, minute=0, second=0, microsecond=0)
            return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        for hour in reversed(self._hours):
            if hour < dt.hour:
                return dt.replace(hour=hour, minute=59, second=0, microsecond=0)
        return (dt - timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)

    def _jump_minute(self, dt: datetime, forward: bool) -> datetime:
        if forward:
            for minute in self._minutes:
                if minute > dt.minute:
                    return dt.replace(minute=minute, second=0, microsecond=0)
            return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        for minute in reversed(self._minutes):
            if minute < dt.minute:
                return dt.replace(minute=minute, second=0, microsecond=0)
        return (dt - timedelta(hours=1)).replace(minute=59, second=0, microsecond=0)


class CronScheduler:
    """State machine that decides which cron ticks have elapsed since the last call.

    Designed to be invoked once per ``AgentCheck.check()`` from the Agent's
    polling loop. ``due_ticks(now)`` is non-blocking: it inspects the cached
    next tick against ``now``, returns all elapsed ticks immediately, and
    advances internal state. It never sleeps.

    With ``startup_lookback > 0``, the first call also recovers the most
    recent past tick when it falls within ``now - startup_lookback`` — useful
    for surviving check restarts mid-cycle.
    """

    __slots__ = ("_expression", "_next_tick_cached", "_startup_lookback")

    def __init__(
        self,
        expression: str | CronExpression,
        *,
        startup_lookback: float = 0.0,
    ) -> None:
        if isinstance(expression, CronExpression):
            self._expression = expression
        elif isinstance(expression, str):
            self._expression = CronExpression(expression)
        else:
            raise TypeError(f"expression must be str or CronExpression, got {type(expression).__name__}")
        if startup_lookback < 0:
            raise ValueError("startup_lookback must be non-negative")
        self._startup_lookback = float(startup_lookback)
        self._next_tick_cached: float | None = None

    @property
    def expression(self) -> CronExpression:
        """The underlying parsed cron expression."""
        return self._expression

    @property
    def next_tick(self) -> float | None:
        """Cached upcoming tick, or None before the first ``due_ticks`` call."""
        return self._next_tick_cached

    def due_ticks(self, now: float | None = None) -> Iterator[float]:
        """Return an iterator over scheduled ticks that have elapsed by ``now``."""
        if now is None:
            now = time.time()

        elapsed: list[float] = []

        if self._next_tick_cached is None:
            if self._startup_lookback > 0:
                prev = self._expression.previous_tick(before=now)
                if now - prev <= self._startup_lookback:
                    elapsed.append(prev)
            self._next_tick_cached = self._expression.next_tick(after=now)
            return iter(elapsed)

        while now >= self._next_tick_cached:
            tick = self._next_tick_cached
            self._next_tick_cached = self._expression.next_tick(after=tick)
            elapsed.append(tick)

        return iter(elapsed)


__all__ = ["CronExpression", "CronScheduler"]
