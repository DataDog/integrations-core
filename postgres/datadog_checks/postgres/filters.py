# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations


def regex_exclude_clauses(column: str, patterns: list[str] | None) -> str:
    """Build SQL fragment of `AND col !~ '<pattern>'` clauses, one per pattern."""
    if not patterns:
        return ""
    return "".join(" AND {} !~ '{}'".format(column, p) for p in patterns)


def regex_include_clause(column: str, patterns: list[str] | None) -> str:
    """Build SQL fragment `AND (col ~ '<p1>' OR col ~ '<p2>' ...)` matching any pattern."""
    if not patterns:
        return ""
    or_clause = " OR ".join("{} ~ '{}'".format(column, p) for p in patterns)
    return f" AND ({or_clause})"
