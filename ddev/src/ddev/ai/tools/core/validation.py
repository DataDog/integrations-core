# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pydantic import ValidationError
from pydantic_core import ErrorDetails


def format_validation_error(exc: ValidationError) -> str:
    """Build a compact, model-facing message from a pydantic ValidationError.

    Drops the pydantic docs URL and the echoed input value, and renders each
    failing field as ``<loc-path>: <reason>`` with list indices in brackets
    (e.g. ``assignments[0].name``).
    """
    errors = exc.errors(include_url=False, include_input=False)
    count = len(errors)
    header = "1 validation error:" if count == 1 else f"{count} validation errors:"
    lines = [_format_error(error) for error in errors]
    return "\n".join([header, *lines])


def _format_error(error: ErrorDetails) -> str:
    loc = _format_loc(error["loc"])
    msg = error["msg"]
    return f"- {loc}: {msg}" if loc else f"- {msg}"


def _format_loc(loc: tuple[str | int, ...]) -> str:
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            parts.append(f"[{item}]")
        elif parts:
            parts.append(f".{item}")
        else:
            parts.append(str(item))
    return "".join(parts)
