# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path


def saved_files(root: Path) -> list[Path]:
    """Every file below `root`, including leftover partial files."""
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []
