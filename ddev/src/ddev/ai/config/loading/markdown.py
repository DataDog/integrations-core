# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

import frontmatter
import yaml

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.files import MarkdownFile, read_utf8


def parse_markdown(path: Path) -> MarkdownFile | None:
    """Parse a Markdown file's YAML front matter, or return None if it has none.

    Malformed, unterminated, or non-mapping front matter is surfaced as a ``ConfigError``.
    """
    text = read_utf8(path)

    handler = frontmatter.YAMLHandler()
    if not handler.detect(text):
        return None

    try:
        raw_meta, body = handler.split(text)
    except ValueError as e:
        raise ConfigError(f"{path}: unterminated YAML front matter") from e

    try:
        meta = handler.load(raw_meta)
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    if not isinstance(meta, dict):
        raise ConfigError(f"{path}: YAML front matter must be a mapping")

    return MarkdownFile(path=path, meta=meta, body=body.strip())
