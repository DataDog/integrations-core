# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ddev.ai.config.errors import FlowConfigError


def parse_md_file(path: Path) -> tuple[dict[str, Any], str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise FlowConfigError(f"Cannot read {path}: {e}") from e

    if not text.startswith("---\n"):
        raise FlowConfigError(f"{path}: missing YAML front matter (file must start with '---')")

    remainder = text[4:]
    for delimiter in ("\n---\n", "\n---"):
        if delimiter in remainder:
            raw_yaml, raw_body = remainder.split(delimiter, 1)
            break
    else:
        raise FlowConfigError(f"{path}: missing YAML front matter closing '---'")

    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise FlowConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    if not isinstance(meta, dict):
        raise FlowConfigError(f"{path}: YAML front matter must be a mapping")

    return meta, raw_body.strip()
