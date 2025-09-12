# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from .base import CacheKey


class FullConfigCacheKey(CacheKey):
    """
    Cache key based on the check_id of the check where it is being used.

    The check_id includes a digest of the full configuration of the check. The cache is invalidated
    whenever the configuration of the check changes.
    """

    def key(self) -> str:
        return self.check.check_id

    def base_key(self) -> str:
        return self.check.check_id
