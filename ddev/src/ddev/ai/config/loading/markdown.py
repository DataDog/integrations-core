# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

import yaml

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.files import MarkdownFile


def parse_markdown(path: Path) -> MarkdownFile | None:
    """Parse a Markdown file's YAML front matter, or return None if it has none."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Cannot read {path}: {e}") from e

    if not text.startswith("---\n"):
        return None

    remainder = text[4:]
    for delimiter in ("\n---\n", "\n---"):
        if delimiter in remainder:
            raw_yaml, raw_body = remainder.split(delimiter, 1)
            break
    else:
        raise ConfigError(f"{path}: missing YAML front matter closing '---'")

    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    if not isinstance(meta, dict):
        raise ConfigError(f"{path}: YAML front matter must be a mapping")

    return MarkdownFile(path=path, meta=meta, body=raw_body.strip())
