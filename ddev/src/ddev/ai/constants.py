# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

CORE_FLOWS_DIR: Path = Path(__file__).parent / "flows"
CORE_PHASES_DIR: Path = Path(__file__).parent / "phases"
CORE_PHASES_PACKAGE: str = f"{__package__}.phases"
