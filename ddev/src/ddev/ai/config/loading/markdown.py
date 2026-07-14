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
    """Parse a Markdown file's YAML front matter, or return None if it has none."""
    text = read_utf8(path)

    if not frontmatter.checks(text):
        return None

    try:
        meta, body = frontmatter.parse(text)
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    return MarkdownFile(path=path, meta=meta, body=body)
