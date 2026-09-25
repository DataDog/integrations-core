# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

BANNER_ERROR_MAX_CHARS = 200


def compact_error_detail(error: BaseException | str, phase_id: str | None = None) -> str:
    """Return the first useful error line, compacted for summary views."""
    fallback = type(error).__name__ if isinstance(error, BaseException) else "Unknown error"
    detail = next((line.strip() for line in str(error).splitlines() if line.strip()), fallback)
    if phase_id is not None:
        detail = detail.removeprefix(f"Phase '{phase_id}' failed: ")
        detail = detail.removeprefix(f"Phase '{phase_id}': ")
    if len(detail) > BANNER_ERROR_MAX_CHARS:
        detail = f"{detail[: BANNER_ERROR_MAX_CHARS - 1].rstrip()}…"
    return detail
