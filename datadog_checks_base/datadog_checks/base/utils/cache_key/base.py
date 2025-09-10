# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck


class CacheKey(ABC):
    def __init__(self, check: AgentCheck):
        """Abstract base class for cache keys management.

        Any implementation of this class provides the logic to generate cache keys to be used in the Agent persistent
        cache.
        """
        self.check = check

    @abstractmethod
    def base_key(self) -> str:
        """
        Abstract method that derives the cache key for the particular implementation.
        This method must return a stable key that only differs between instances based on the
        specific implmentation of the invalidation logic.
        """

    def key_for(self, context: str) -> str:
        """
        Returns a key that is a combination of the base key and the provided context.
        """
        return f"{self.base_key()}_{context}"
