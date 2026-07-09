# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MarkdownFile:
    """A Markdown file with parsed YAML front matter and its stripped body."""

    path: Path
    meta: dict[str, Any]
    body: str


@dataclass(frozen=True)
class YamlFile:
    """A YAML file that parsed to a top-level list of documents."""

    path: Path
    docs: list[Any]


@dataclass(frozen=True)
class FileError:
    """A file that signalled config intent but could not be parsed."""

    path: Path
    message: str


type LoadedFile = MarkdownFile | YamlFile
