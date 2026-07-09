# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

import yaml

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.loading.files import YamlFile


def load_yaml(path: Path) -> YamlFile | None:
    """Parse a YAML file, returning None unless it parses to a top-level list."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise FlowConfigError(f"Cannot read {path}: {e}") from e

    try:
        docs = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise FlowConfigError(f"{path}: invalid YAML: {e}") from e

    if not isinstance(docs, list):
        return None

    return YamlFile(path=path, docs=docs)
