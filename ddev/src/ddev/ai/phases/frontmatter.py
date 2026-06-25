# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

import yaml

from ddev.ai.phases.config import FlowConfigError


def parse_md_file(path: Path) -> tuple[dict[str, Any], str]:
    """Parse a Markdown file with YAML front matter.

    Returns (front_matter_dict, body_str). Raises FlowConfigError on any problem.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise FlowConfigError(f"Cannot read {path}: {e}") from e

    if not text.startswith("---"):
        raise FlowConfigError(f"{path}: missing YAML front matter (file must start with '---')")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise FlowConfigError(f"{path}: missing YAML front matter closing '---'")

    _, raw_yaml, raw_body = parts
    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise FlowConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    return meta, raw_body.strip()
