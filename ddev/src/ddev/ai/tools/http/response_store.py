# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import codecs
import itertools
import json
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from pydantic import JsonValue


class ResponseStoreError(Exception):
    """Raised when a response cannot be saved."""


@dataclass(frozen=True)
class SavedResponse:
    path: Path
    metadata_path: Path
    lines: int


class ResponseStore:
    """Writes HTTP response snapshots and their metadata sidecars into one directory.

    One instance is shared by every HTTP tool in an execution. The store never overwrites
    existing files and returns a path only after both the body and its sidecar were written.
    Failed streaming saves remove their own partial artifacts.
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
        path, metadata_path = self._paths(suffix=suffix, stem=stem)

        _write_new(path, _encode(body))
        try:
            _write_new(metadata_path, _encode(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"))
        except ResponseStoreError:
            path.unlink(missing_ok=True)
            raise
        return SavedResponse(path=path, metadata_path=metadata_path, lines=_count_lines(body))

    async def save_stream(
        self,
        *,
        chunks: AsyncIterator[bytes],
        charset: str | None,
        metadata: dict[str, JsonValue],
        stem: str,
        max_bytes: int,
    ) -> tuple[SavedResponse, int]:
        """Decode chunks to a new text file, publishing metadata only on completion.

        Return the saved paths and line count, plus the byte count, without rereading or parsing
        the body. Interruptions remove owned partial files. The cap counts bytes after HTTP
        decompression, before charset decoding.
        """
        try:
            decoder = codecs.getincrementaldecoder(charset or "utf-8")(errors="replace")
        except LookupError:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        received_bytes = 0
        path, metadata_path = self._paths(suffix=".txt", stem=stem)
        owned = False
        complete = False
        newlines = 0
        last_char = ""
        try:
            with path.open("xb") as file:
                owned = True
                async for chunk in chunks:
                    received_bytes += len(chunk)
                    if received_bytes > max_bytes:
                        raise ResponseStoreError(
                            f"Response exceeded the {max_bytes}-byte download limit and was discarded"
                        )
                    text = decoder.decode(chunk)
                    file.write(_encode(text))
                    newlines += text.count("\n")
                    last_char = text[-1:] or last_char
                tail = decoder.decode(b"", final=True)
                file.write(_encode(tail))
                newlines += tail.count("\n")
                last_char = tail[-1:] or last_char
            metadata = {**metadata, "received_bytes": received_bytes, "complete": True}
            _write_new(metadata_path, _encode(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"))
            complete = True
            # A final line without a trailing newline still counts as a line.
            lines = newlines + (1 if last_char not in ("", "\n") else 0)
            return SavedResponse(path, metadata_path, lines), received_bytes
        except FileExistsError as e:
            raise ResponseStoreError(f"Refusing to overwrite existing response file {path}") from e
        except OSError as e:
            raise ResponseStoreError(f"Cannot write response file {path}: {e}") from e
        finally:
            if owned and not complete:
                path.unlink(missing_ok=True)

    def _paths(self, *, suffix: str, stem: str) -> tuple[Path, Path]:
        name = f"{next(self._sequence):04d}-{stem}-{uuid.uuid4().hex[:8]}"
        path = self._root / f"{name}{suffix}"
        metadata_path = self._root / f"{name}.meta.json"
        try:
            self._root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise ResponseStoreError(f"Cannot create response directory: {e}") from e

        return path, metadata_path


def _count_lines(text: str) -> int:
    """Count lines the way `grep` numbers them: a final line without a trailing newline counts."""
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def _encode(text: str) -> bytes:
    # Parsed JSON can hold lone surrogates (from escapes like "\ud800") that UTF-8 cannot encode;
    # backslashreplace writes them back as the same escape, so saved JSON stays valid and lossless.
    return text.encode("utf-8", errors="backslashreplace")


def _write_new(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as f:
            f.write(data)
    except FileExistsError as e:
        raise ResponseStoreError(f"Refusing to overwrite existing response file {path}") from e
    except OSError as e:
        path.unlink(missing_ok=True)
        raise ResponseStoreError(f"Cannot write response file {path}: {e}") from e
