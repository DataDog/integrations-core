# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from typing import Optional

try:
    from datadog_agent import read_persistent_cache, write_persistent_cache
except ImportError:

    def write_persistent_cache(key, value):
        # type: (str, str) -> None
        pass

    def read_persistent_cache(key):
        # type: (str) -> Optional[str]
        return ''
