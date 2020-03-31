# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Built-in value transformers.
"""
import datetime as dt
from typing import Any, Sequence

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import ServiceCheckStatus
from datadog_checks.base.utils.db.utils import normalize_datetime


def length(value):
    # type: (Sequence) -> int
    return len(value)


def to_time_elapsed(datetime):
    # type: (dt.datetime) -> float
    datetime = normalize_datetime(datetime)
    elapsed = dt.datetime.now(datetime.tzinfo) - datetime
    return elapsed.total_seconds()


def ok_warning(value):
    # type: (Any) -> ServiceCheckStatus
    return AgentCheck.OK if value else AgentCheck.WARNING
