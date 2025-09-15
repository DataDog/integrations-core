# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck


class CacheInvalidationStrategy(ABC):
    """
    Abstract base class for cache invalidation strategies.

    Implementations of this class encapsulate the logic for cache invalidation used for the agent persistent cache.
    """

    def __init__(self, check: AgentCheck):
        self.check = check
        self.__cache_key: str | None = None

    def key_prefix(self) -> str:
        """
        Returns the cache key preffix for the particular implementation.
        """
        if self.__cache_key is not None:
            return self.__cache_key

        check_id_prefix = ":".join(self.check.check_id.split(":")[:-1])
        self.__cache_key = f"{check_id_prefix}_{self.invalidation_token()}"

        return self.__cache_key

    @abstractmethod
    def invalidation_token(self) -> str:
        """
        Abstract method that returns the invalidation token for the particular implementation.
        This method must return a stable token that only differs between instances based on the
        specific implmentation of the invalidation logic.
        """
