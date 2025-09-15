# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from .invalidation_strategy import CacheInvalidationStrategy


class FullConfigInvalidationStrategy(CacheInvalidationStrategy):
    """
    Cache invalidation strategy based on the check_id of the check where it is being used.

    The check_id includes a digest of the full configuration of the check. The cache is invalidated
    whenever the configuration of the check changes.
    """

    def key_preffix(self) -> str:
        return self.invalidation_token()

    def invalidation_token(self) -> str:
        return self.check.check_id
