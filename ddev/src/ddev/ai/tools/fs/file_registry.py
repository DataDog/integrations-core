# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import hashlib
from pathlib import Path


class FileRegistry:
    """Tracks files created by the agent and their last-seen content hash."""

    def __init__(self) -> None:
        self._hashes: dict[str, str] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _normalize(self, path: str) -> str:
        return Path(path).resolve().as_posix()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def record(self, path: str, content: str) -> None:
        self._hashes[self._normalize(path)] = self._hash(content)

    def is_known(self, path: str) -> bool:
        return self._normalize(path) in self._hashes

    def get_lock(self, path: str) -> asyncio.Lock:
        normalized = self._normalize(path)
        if normalized not in self._locks:
            self._locks[normalized] = asyncio.Lock()
        return self._locks[normalized]

    def verify(self, path: str, content: str) -> bool:
        """Check whether content matches what was last recorded for path."""
        normalized = self._normalize(path)
        stored = self._hashes.get(normalized)
        return stored is not None and self._hash(content) == stored
