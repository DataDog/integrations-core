# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any

try:
    from datadog_checks.base.utils.common import total_time_to_temporal_percent
except ImportError:

    # Provide fallback for agent < 6.16
    def total_time_to_temporal_percent(total_time, scale=1000):  # type: ignore
        return total_time / scale * 100


try:
    from datadog_agent import get_config, read_persistent_cache, write_persistent_cache
except ImportError:

    def get_config(value):
        # type: (Any) -> str
        return ''

    def write_persistent_cache(value, key):
        # type: (Any, Any) -> None
        pass

    def read_persistent_cache(value):
        # type: (Any) -> str
        return ''
