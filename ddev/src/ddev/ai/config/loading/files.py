# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ddev.ai.config.errors import ConfigError


def read_utf8(path: Path) -> str:
    """Read a UTF-8 config file and normalize filesystem and decoding errors."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ConfigError(f"{path}: file is not valid UTF-8: {e}") from e
    except OSError as e:
        raise ConfigError(f"Cannot read {path}: {e}") from e


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
