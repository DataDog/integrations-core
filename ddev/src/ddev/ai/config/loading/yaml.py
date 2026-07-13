# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

import yaml

from ddev.ai.config.errors import ConfigError
from ddev.ai.config.loading.files import YamlFile


def load_yaml(path: Path) -> YamlFile | None:
    """Parse a YAML file into its documents, or None if it holds no addressable ones.

    A top-level list is its documents; a bare mapping is a single document (so one
    resource need not be wrapped in a list). A scalar or empty file carries no document
    that could declare a ``type``, so it is not a config file. Deciding whether a
    document is actually config is left to classification.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Cannot read {path}: {e}") from e

    try:
        docs = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: invalid YAML: {e}") from e

    if isinstance(docs, dict):
        return YamlFile(path=path, docs=[docs])
    if isinstance(docs, list):
        return YamlFile(path=path, docs=docs)
    return None
