# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

from datadog_checks.base.utils.containers import hash_mutable

from .base import CacheKey

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck


class ConfigSetCacheKey(CacheKey):
    """
    Cache key that invalidates the cache when a subset of the check's config options changes.

    Parameters:
        check: the check instance the key is going to be used for.
        init_config_options: the subset of init_config options to use to generate the cache key.
        instance_config_options: the subset of config options to use to generate the cache key.
    """

    def __init__(
        self,
        check: AgentCheck,
        *,
        init_config_options: Collection[str] | None = None,
        instance_config_options: Collection[str] | None = None,
    ):
        super().__init__(check)
        self.init_config_options = set(init_config_options) if init_config_options else set()
        self.instance_config_options = set(instance_config_options) if instance_config_options else set()

        if not self.init_config_options and not self.instance_config_options:
            raise ValueError("At least one of init_config_options or instance_config_options must be provided")

        # Config cannot change on the fly, so we can cache the key
        self.__key: str | None = None

    def base_key(self) -> str:
        if self.__key is not None:
            return self.__key

        init_config_values = tuple(
            value for key, value in self.check.init_config.items() if key in self.init_config_options
        )
        instance_config_values = tuple(
            value for key, value in self.check.instance.items() if key in self.instance_config_options
        )

        selected_values = init_config_values + instance_config_values
        self.__key = str(hash_mutable(selected_values)).replace("-", "")
        return self.__key
