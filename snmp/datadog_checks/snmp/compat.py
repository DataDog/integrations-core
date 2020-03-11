# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any, Optional

try:
    from datadog_checks.base.utils.common import total_time_to_temporal_percent
except ImportError:

    # Provide fallback for agent < 6.16
    def total_time_to_temporal_percent(total_time, scale=1000):  # type: ignore
        return total_time / scale * 100


try:
    from datadog_agent import get_config, read_persistent_cache, write_persistent_cache
except ImportError:

    def get_config(key):
        # type: (str) -> Optional[str]
        return ''

    def write_persistent_cache(key, value):
        # type: (str, str) -> None
        pass

    def read_persistent_cache(key):
        # type: (str) -> Optional[str]
        return ''
