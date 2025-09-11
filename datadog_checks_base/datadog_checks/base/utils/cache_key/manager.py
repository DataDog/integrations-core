# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from datadog_checks.base import AgentCheck

from .base import CacheKey
from .full_config import FullConfigCacheKey


class CacheKeyType(Enum):
    """Enum used to identify the type of cache key."""

    LOG_CURSOR = auto()


class CacheKeyManager:
    def __init__(self, check: AgentCheck):
        """
        Manager of cache keys for the persistent cache.

        This class defined the different kinds of persistent cache keys to be used when adding and retrieving
        from the agent persistent cache. The AgentCheck can use this manager to to ensure that the correct cache key is
        used in each consistently through the different check invocations.
        """
        self.keys: dict[CacheKeyType, CacheKey] = {}
        self.check = check
        self.default_cache_key = FullConfigCacheKey(self.check)

    def __retrieve_cache_key(
        self,
        key_type: CacheKeyType,
        default_factory: Callable[[], CacheKey] | None = None,
    ) -> CacheKey:
        if (key := self.keys.get(key_type)) is not None:
            return key

        self.keys[key_type] = default_factory() if default_factory is not None else self.default_cache_key
        return self.keys[key_type]

    def has_cache_key(self, key_type: CacheKeyType) -> bool:
        return key_type in self.keys

    def get(self, *, cache_key_type: CacheKeyType, default_factory: Callable[[], CacheKey] | None = None) -> CacheKey:
        """
        Returns the cache key for the given cache key type.
        """
        return self.__retrieve_cache_key(
            key_type=cache_key_type,
            default_factory=default_factory,
        )

    def add(self, *, cache_key_type: CacheKeyType, key_factory: Callable[[], CacheKey], override: bool = False):
        """
        Adds the cache key for the given cache key type.

        The provided cache key is only added if the cache key type is not already in the manager. To force the addition
        of the cache key, set the `override` argument to `True`.
        """
        if cache_key_type in self.keys and not override:
            return
        self.keys[cache_key_type] = key_factory()
