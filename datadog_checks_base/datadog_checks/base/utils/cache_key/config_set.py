# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

from .base import CacheKey

if TYPE_CHECKING:
    from typing import Any, Iterable

    from datadog_checks.base import AgentCheck


class ConfigSetCacheKey(CacheKey):
    """
    Cache key that is derived from a subset of the check's config options.

    When the subset of config options changes, the cache is invalidated.
    """

    def __init__(
        self,
        check: AgentCheck,
        config_options: Collection[str],
    ):
        super().__init__(check)
        self.config_options = set(config_options)
        # Config cannot change on the fly, so we can cache the key
        self.__key: str | None = None

    def base_key(self) -> str:
        if self.__key is not None:
            return self.__key

        merged_config = self.check.init_config | self.check.instance
        selected_values = tuple(values for key, values in merged_config.items() if key in self.config_options)
        self.__key = str(hash(self.__sorted_values(selected_values)))
        return self.__key

    def __sorted_values(self, values: Iterable[Any]) -> tuple[str, ...]:
        sorted_values = []

        for value in values:
            if isinstance(value, (list, tuple, set, frozenset)):
                sorted_values.extend(self.__sorted_values(value))
            elif isinstance(value, dict):
                for key, dict_value in value.items():
                    sorted_values.append(f"{key}:{self.__sorted_values(dict_value)}")
            else:
                sorted_values.append(str(value))
        return tuple(sorted(sorted_values))
