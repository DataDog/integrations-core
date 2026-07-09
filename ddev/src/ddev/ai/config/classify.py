# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ddev.ai.config.loading.files import FileError, LoadedFile
    from ddev.ai.config.registry import Entry


@dataclass(frozen=True)
class ClassifyOutput:
    """The typed entries and file errors produced from one loaded file."""

    entries: list[Entry[Any]] = field(default_factory=list)
    file_errors: list[FileError] = field(default_factory=list)


def classify(loaded: LoadedFile) -> ClassifyOutput:
    """Turn one loaded file into zero or more identity-carrying entries.

    Driven by the type table: a resource's kind comes from its ``type`` tag, the format
    gates the legal type subset, and ``name`` is required identity. Touches no filesystem
    and cross-references nothing.
    """
    raise NotImplementedError
