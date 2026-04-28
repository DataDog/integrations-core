# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import hashlib

from .file_access_policy import FileAccessPolicy, canonicalize_path


class FileRegistry:
    """Tracks the files each owner has seen, along with their last-seen content hash.

    One FileRegistry is intended to be shared across all owners in a run. Hashes
    are partitioned by owner_id so that each owner must independently read or
    create a file before modifying it; reads by owner A never authorize writes
    by owner B. Only SHA-256 digests are stored (not file contents).

    Path-level locks are shared across owners so that concurrent writes to the
    same file are serialized regardless of which owner initiated them.

    _hashes layout: {owner_id: {normalized_path: sha256_hex}}.
    _locks and _hashes grow for the registry's lifetime and are never evicted.
    """

    def __init__(self, policy: FileAccessPolicy | None = None) -> None:
        self._policy = policy if policy is not None else FileAccessPolicy()
        self._hashes: dict[str, dict[str, str]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @property
    def policy(self) -> FileAccessPolicy:
        return self._policy

    def _normalize(self, path: str) -> str:
        return canonicalize_path(path).as_posix()

    def _hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def record(self, owner_id: str, path: str, content: str) -> None:
        self._hashes.setdefault(owner_id, {})[self._normalize(path)] = self._hash(content)

    def is_known(self, owner_id: str, path: str) -> bool:
        return self._normalize(path) in self._hashes.get(owner_id, {})

    def verify(self, owner_id: str, path: str, content: str) -> bool:
        """Check whether content matches what this agent last recorded for path."""
        stored = self._hashes.get(owner_id, {}).get(self._normalize(path))
        return stored is not None and self._hash(content) == stored

    def lock_for(self, path: str) -> asyncio.Lock:
        # Safe under single-threaded asyncio; asyncio.Lock is not thread-safe.
        # Path-level (not agent-scoped) so concurrent writes from different agents serialize.
        return self._locks.setdefault(self._normalize(path), asyncio.Lock())
