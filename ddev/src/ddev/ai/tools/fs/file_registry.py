# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import hashlib
from pathlib import Path

from .file_access_policy import FileAccessPolicy


class FileRegistry:
    """Tracks the files each agent has seen, along with their last-seen content hash.

    One FileRegistry is intended to be shared across all agents in a run. Hashes
    are partitioned by agent_id so that each agent must independently read or
    create a file before modifying it; reads by agent A never authorize writes
    by agent B. Only SHA-256 digests are stored (not file contents).

    Path-level locks are shared across agents so that concurrent writes to the
    same file are serialized regardless of which agent initiated them.
    """

    def __init__(self, policy: FileAccessPolicy | None = None) -> None:
        self._policy = policy if policy is not None else FileAccessPolicy()
        self._hashes: dict[str, dict[str, str]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def policy(self) -> FileAccessPolicy:
        return self._policy

    def _normalize(self, path: str) -> str:
        return Path(path).resolve().as_posix()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def record(self, agent_id: str, path: str, content: str) -> None:
        self._hashes.setdefault(agent_id, {})[self._normalize(path)] = self._hash(content)

    def is_known(self, agent_id: str, path: str) -> bool:
        return self._normalize(path) in self._hashes.get(agent_id, {})

    def verify(self, agent_id: str, path: str, content: str) -> bool:
        """Check whether content matches what this agent last recorded for path."""
        stored = self._hashes.get(agent_id, {}).get(self._normalize(path))
        return stored is not None and self._hash(content) == stored

    def lock_for(self, path: str) -> asyncio.Lock:
        # Safe under single-threaded asyncio; asyncio.Lock is not thread-safe.
        # Path-level (not agent-scoped) so concurrent writes from different agents serialize.
        return self._locks.setdefault(self._normalize(path), asyncio.Lock())
