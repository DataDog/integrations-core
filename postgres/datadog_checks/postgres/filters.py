# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations


def regex_exclude_clauses(column: str, patterns: list[str] | None) -> str:
    """Build SQL fragment of `AND col !~ %s` clauses, one per pattern.

    Caller is responsible for binding `patterns` as parameters when executing.
    """
    if not patterns:
        return ""
    return "".join(" AND {} !~ %s".format(column) for _ in patterns)


def regex_include_clause(column: str, patterns: list[str] | None) -> str:
    """Build SQL fragment `AND (col ~ %s OR col ~ %s ...)` matching any pattern.

    Caller is responsible for binding `patterns` as parameters when executing.
    """
    if not patterns:
        return ""
    or_clause = " OR ".join("{} ~ %s".format(column) for _ in patterns)
    return f" AND ({or_clause})"
