# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable, Mapping
from typing import Protocol

from ddev.ai.phases.resources import ResourceUnavailableError


class TokenProducer(Protocol):
    """Supply credentials for the run's fixed route."""

    async def token_for(self, provider: str) -> str: ...

    def reject(self, token: str) -> None:
        """Invalidate a matching credential if the producer supports replacement."""
        ...

    def clear(self) -> None: ...


class DirectTokenProducer:
    """Load each provider's configured key on demand and keep it for the run."""

    def __init__(self, key_loaders: Mapping[str, Callable[[], str | None]]) -> None:
        self._key_loaders = key_loaders
        self._keys: dict[str, str] = {}

    def has_key(self, provider: str) -> bool:
        return self._load_key(provider) is not None

    async def token_for(self, provider: str) -> str:
        key = self._load_key(provider)
        if key is None:
            raise ResourceUnavailableError(f"No direct credential is configured for {provider}.")
        return key

    def reject(self, token: str) -> None:
        """Keep using the configured key; direct credentials cannot be refreshed."""

    def clear(self) -> None:
        self._keys.clear()

    def _load_key(self, provider: str) -> str | None:
        if provider not in self._keys:
            load = self._key_loaders.get(provider)
            key = load() if load is not None else None
            if not key or not key.strip():
                return None
            self._keys[provider] = key
        return self._keys[provider]
