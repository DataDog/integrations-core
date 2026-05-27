# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_property_result(
    property_dir: Path,
    *,
    property_name: str,
    artifacts: list[dict[str, str]],
    status: str = 'passed',
    counts: dict[str, Any] | None = None,
) -> None:
    """Write a small manifest describing artifacts emitted by one replay-PBT property.

    CI aggregation consumes this manifest instead of maintaining hard-coded lists
    of property-specific output filenames. Artifact paths are relative to
    ``property_dir``.
    """
    property_dir.mkdir(parents=True, exist_ok=True)
    (property_dir / 'property-result.json').write_text(
        json.dumps(
            {
                'property': property_name,
                'status': status,
                'artifacts': artifacts,
                'counts': counts or {},
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )
