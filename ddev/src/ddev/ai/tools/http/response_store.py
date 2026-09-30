# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import itertools
import json
import os
import tempfile
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

DEFAULT_QUOTA_BYTES: Final = 100 * 1024 * 1024
RESPONSES_DIR_NAME: Final = "responses"


class ResponseStoreError(Exception):
    """Raised when a response cannot be saved (quota exhausted, filesystem failure, confinement)."""


@dataclass(frozen=True)
class SavedResponse:
    path: Path
    metadata_path: Path
    size: int


def new_execution_id() -> str:
    """A sortable, unique ID for one launch or resume of a run."""
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


class ResponseStore:
    """Writes immutable HTTP response snapshots under one execution's directory.

    One instance is shared by every HTTP tool in an execution, so quota accounting and name
    allocation are coordinated across agents without sharing response bodies in memory. Files are
    never overwritten, and a path is returned only after both the body and its metadata sidecar
    were written completely. Nothing here removes earlier evidence.
    """

    def __init__(self, run_root: Path, execution_id: str, quota_bytes: int = DEFAULT_QUOTA_BYTES) -> None:
        self._run_root = run_root
        self._root = run_root / RESPONSES_DIR_NAME / execution_id
        self._quota = quota_bytes
        self._used = 0
        self._lock = threading.Lock()
        self._sequence = itertools.count(1)
        self._root_ready = False

    @property
    def root(self) -> Path:
        return self._root

    def save(self, *, body: str, suffix: str, metadata: dict[str, object], stem: str) -> SavedResponse:
        """Atomically write `body` and a metadata sidecar; raise `ResponseStoreError` on any failure."""
        body_bytes = body.encode("utf-8")
        name = f"{next(self._sequence):04d}-{stem}-{uuid.uuid4().hex[:8]}"
        # Metadata records the saved size, which is only known after encoding the body.
        metadata = {**metadata, "saved_bytes": len(body_bytes)}
        meta_bytes = (json.dumps(metadata, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8")
        size = len(body_bytes) + len(meta_bytes)

        with self._reserve(size):
            root = self._ensure_root()
            path = root / f"{name}{suffix}"
            metadata_path = root / f"{name}.meta.json"
            _write_new(path, body_bytes)
            try:
                _write_new(metadata_path, meta_bytes)
            except BaseException:
                path.unlink(missing_ok=True)
                raise
        return SavedResponse(path=path, metadata_path=metadata_path, size=size)

    @contextmanager
    def _reserve(self, size: int) -> Iterator[None]:
        with self._lock:
            if self._used + size > self._quota:
                raise ResponseStoreError(
                    f"Response storage quota exhausted ({self._used} of {self._quota} bytes used); "
                    "earlier responses were kept"
                )
            self._used += size
        try:
            yield
        except BaseException:
            with self._lock:
                self._used -= size
            raise

    def _ensure_root(self) -> Path:
        with self._lock:
            if not self._root_ready:
                try:
                    self._root.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ResponseStoreError(f"Cannot create response directory: {e}") from e
                if self._root.is_symlink() or not self._root.resolve().is_relative_to(self._run_root.resolve()):
                    raise ResponseStoreError(f"Response directory escapes the run directory: {self._root}")
                self._root_ready = True
        return self._root


def _write_new(path: Path, data: bytes) -> None:
    """Write `data` to a temporary file and link it to `path`, failing if `path` already exists."""
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".partial-")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # os.link refuses to replace an existing file, unlike os.replace.
        os.link(tmp, path)
    except FileExistsError as e:
        raise ResponseStoreError(f"Refusing to overwrite existing response file {path}") from e
    except OSError as e:
        raise ResponseStoreError(f"Cannot write response file {path}: {e}") from e
    finally:
        tmp.unlink(missing_ok=True)
