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

    def base_key(self) -> str:
        # The check_id is injected by the agent containing the config digest
        return str(self.check.check_id)
