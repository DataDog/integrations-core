# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import itertools
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from pydantic import JsonValue


class ResponseStoreError(Exception):
    """Raised when a response cannot be saved."""


@dataclass(frozen=True)
class SavedResponse:
    path: Path
    metadata_path: Path


class ResponseStore:
    """Writes HTTP response snapshots and their metadata sidecars into one directory.

    One instance is shared by every HTTP tool in an execution. The store never overwrites or
    deletes files, and returns a path only after both the body and its sidecar were written.
    That is a guarantee about the store only: agents can still modify the files with their file
    tools, and a fresh (non-resume) launch removes the whole run directory.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._sequence = itertools.count(1)

    @property
    def root(self) -> Path:
        return self._root

    def save(self, *, body: str, suffix: str, metadata: dict[str, JsonValue], stem: str) -> SavedResponse:
        """Write `body` and a metadata sidecar; raise `ResponseStoreError` on any failure."""
        name = f"{next(self._sequence):04d}-{stem}-{uuid.uuid4().hex[:8]}"
        path = self._root / f"{name}{suffix}"
        metadata_path = self._root / f"{name}.meta.json"
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ResponseStoreError(f"Cannot create response directory: {e}") from e

        _write_new(path, _encode(body))
        try:
            _write_new(metadata_path, _encode(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"))
        except ResponseStoreError:
            path.unlink(missing_ok=True)
            raise
        return SavedResponse(path=path, metadata_path=metadata_path)


def _encode(text: str) -> bytes:
    # Parsed JSON can hold lone surrogates (from escapes like "\ud800") that UTF-8 cannot encode;
    # backslashreplace writes them back as the same escape, so saved JSON stays valid and lossless.
    return text.encode("utf-8", errors="backslashreplace")


def _write_new(path: Path, data: bytes) -> None:
    try:
        with open(path, "xb") as f:
            f.write(data)
    except FileExistsError as e:
        raise ResponseStoreError(f"Refusing to overwrite existing response file {path}") from e
    except OSError as e:
        path.unlink(missing_ok=True)
        raise ResponseStoreError(f"Cannot write response file {path}: {e}") from e
