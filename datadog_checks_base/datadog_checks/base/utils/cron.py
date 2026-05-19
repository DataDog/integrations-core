# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Standard 5-field UTC cron expression parsing and scheduling.

* ``CronExpression`` is the stateless tick calculator. Parse once, then ask
  for the next or previous tick relative to any timestamp.
* ``CronScheduler`` wraps an expression with state to report which scheduled
  ticks have elapsed since the last call.

Only the standard 5-field syntax (minute hour day-of-month month day-of-week)
in UTC is supported. ``@``-aliases, seconds, year, month/day name aliases,
and ``L``/``W``/``#`` extensions are rejected at parse time.
"""

from __future__ import annotations

import re
import time
from calendar import monthrange
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

WHITESPACE_AROUND_COMMA = re.compile(r"\s*,\s*")

MINUTE_RANGE = (0, 59)
HOUR_RANGE = (0, 23)
DOM_RANGE = (1, 31)
MONTH_RANGE = (1, 12)
DOW_RANGE = (0, 7)

MAX_DAYS_PER_MONTH = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

WALK_ITERATION_BUDGET = 366 * 8


def _parse_field(field: str, low: int, high: int) -> tuple[int, ...]:
    """Parse a comma-separated cron field into a sorted tuple of allowed values."""
    if not field:
        raise ValueError("empty cron field")
    values: set[int] = set()
    for chunk in field.split(","):
        values.update(_expand_chunk(chunk, low, high))
    if not values:
        raise ValueError(f"cron field expanded to empty set: {field!r}")
    return tuple(sorted(values))


def _expand_chunk(chunk: str, low: int, high: int) -> range:
    """Expand one comma-separated piece (with optional /step) into a numeric range."""
    if not chunk:
        raise ValueError("empty value in cron field")
    base, step, step_specified = _split_step(chunk)
    start, end = _parse_base(base, low, high, step_specified=step_specified)
    if start < low or end > high:
        raise ValueError(f"value out of range [{low}, {high}] in {chunk!r}")
    return range(start, end + 1, step)


def _split_step(chunk: str) -> tuple[str, int, bool]:
    """Split 'base[/step]' into (base, step, step_specified). step defaults to 1."""
    if "/" not in chunk:
        return chunk, 1, False
    base, _, step_str = chunk.partition("/")
    if not base or not step_str:
        raise ValueError(f"malformed step expression: {chunk!r}")
    try:
        step = int(step_str)
    except ValueError as exc:
        raise ValueError(f"step must be an integer: {chunk!r}") from exc
    if step <= 0:
        raise ValueError(f"step must be positive: {chunk!r}")
    return base, step, True


def _parse_base(base: str, low: int, high: int, *, step_specified: bool) -> tuple[int, int]:
    """Parse the value portion of a chunk into an inclusive (start, end) pair."""
    if base == "*":
        return low, high
    if "-" in base:
        return _parse_range(base)
    try:
        value = int(base)
    except ValueError as exc:
        raise ValueError(f"value must be an integer: {base!r}") from exc
    return (value, high) if step_specified else (value, value)


def _parse_range(base: str) -> tuple[int, int]:
    """Parse an inclusive 'n-m' range into (n, m)."""
    left, _, right = base.partition("-")
    if not left or not right:
        raise ValueError(f"malformed range: {base!r}")
    try:
        start, end = int(left), int(right)
    except ValueError as exc:
        raise ValueError(f"range bounds must be integers: {base!r}") from exc
    if start > end:
        raise ValueError(f"range start must be <= end: {base!r}")
    return start, end


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
            raise TypeError("cron expression must be a string")

        stripped = expression.strip()
        if not stripped:
            raise ValueError("cron expression is empty")
        if stripped.startswith("@"):
            raise ValueError(f"shortcut expressions are not supported: {expression!r}")

        normalized = WHITESPACE_AROUND_COMMA.sub(",", stripped)
        fields = normalized.split()
        if len(fields) != 5:
            raise ValueError(f"expected 5 cron fields, got {len(fields)}: {expression!r}")

        minute_field, hour_field, dom_field, month_field, dow_field = fields

        self._minutes = _parse_field(minute_field, *MINUTE_RANGE)
        self._hours = _parse_field(hour_field, *HOUR_RANGE)
        self._doms = _parse_field(dom_field, *DOM_RANGE)
        self._dom_restricted = dom_field != "*"
        self._months = _parse_field(month_field, *MONTH_RANGE)
        raw_dows = _parse_field(dow_field, *DOW_RANGE)
        self._dow_restricted = dow_field != "*"
        self._dows = tuple(sorted({0 if v == 7 else v for v in raw_dows}))
        self._expression = " ".join(fields)
        self._reject_unsatisfiable_dom_month()

    def _reject_unsatisfiable_dom_month(self) -> None:
        if self._dow_restricted or not self._dom_restricted:
            return
        for month in self._months:
            if any(day <= MAX_DAYS_PER_MONTH[month] for day in self._doms):
                return
        raise ValueError(
            f"cron expression {self._expression!r} can never fire: "
            f"day-of-month {list(self._doms)} does not occur in months {list(self._months)}"
        )

    def _canonical_key(self) -> tuple:
        return (
            self._minutes,
            self._hours,
            self._doms,
            self._months,
            self._dows,
            self._dom_restricted,
            self._dow_restricted,
        )

    def __repr__(self) -> str:
        return f"CronExpression({self._expression!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CronExpression):
            return NotImplemented
        return self._canonical_key() == other._canonical_key()

    def __hash__(self) -> int:
        return hash(self._canonical_key())

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
        raise ValueError(
            f"cron expression {self._expression!r} has no matching tick within {WALK_ITERATION_BUDGET} steps"
        )

    def _jump_month(self, dt: datetime, forward: bool) -> datetime:
        year = dt.year
        if forward:
            for month in self._months:
                if month > dt.month:
                    return datetime(year, month, 1, 0, 0, tzinfo=UTC)
            return datetime(year + 1, self._months[0], 1, 0, 0, tzinfo=UTC)
        for month in reversed(self._months):
            if month < dt.month:
                return datetime(year, month, monthrange(year, month)[1], 23, 59, tzinfo=UTC)
        last = self._months[-1]
        return datetime(year - 1, last, monthrange(year - 1, last)[1], 23, 59, tzinfo=UTC)

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

        last_minute = self._minutes[-1]
        for hour in reversed(self._hours):
            if hour < dt.hour:
                return dt.replace(hour=hour, minute=last_minute, second=0, microsecond=0)
        return (dt - timedelta(days=1)).replace(hour=self._hours[-1], minute=last_minute, second=0, microsecond=0)

    def _jump_minute(self, dt: datetime, forward: bool) -> datetime:
        if forward:
            for minute in self._minutes:
                if minute > dt.minute:
                    return dt.replace(minute=minute, second=0, microsecond=0)
            return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        for minute in reversed(self._minutes):
            if minute < dt.minute:
                return dt.replace(minute=minute, second=0, microsecond=0)
        return (dt - timedelta(hours=1)).replace(minute=self._minutes[-1], second=0, microsecond=0)


class CronScheduler:
    """State machine that reports which cron ticks have elapsed since the last call.

    ``due_ticks(now)`` is non-blocking: it inspects the cached next tick against
    ``now``, returns all elapsed ticks immediately, and advances internal state.
    It never sleeps.

    With ``startup_lookback > 0``, the first call also yields the most recent
    past tick when it falls within ``now - startup_lookback``.
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

    def due_ticks(self, now: float | None = None) -> list[float]:
        """Return scheduled ticks that have elapsed by ``now``."""
        if now is None:
            now = time.time()

        elapsed: list[float] = []

        if self._next_tick_cached is None:
            if self._startup_lookback > 0:
                prev = self._expression.previous_tick(before=now)
                if now - prev <= self._startup_lookback:
                    elapsed.append(prev)
            self._next_tick_cached = self._expression.next_tick(after=now)
            return elapsed

        while now >= self._next_tick_cached:
            tick = self._next_tick_cached
            self._next_tick_cached = self._expression.next_tick(after=tick)
            elapsed.append(tick)

        return elapsed


__all__ = ["CronExpression", "CronScheduler"]
