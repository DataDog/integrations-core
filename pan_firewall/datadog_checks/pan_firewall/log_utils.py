# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter


def warn_once(log: CheckLoggingAdapter, warned: set[str], key: str, msg: str, *args: object) -> None:
    """Log the warning the first time `key` is seen in `warned`, at debug level after that: a condition that lasts
    would otherwise repeat it on every run."""
    emit = log.debug if key in warned else log.warning
    warned.add(key)
    emit(msg, *args)
