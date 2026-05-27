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
    validation_family: str | None = None,
    requires_replay_cache: bool | None = None,
) -> None:
    """Write a small manifest describing artifacts emitted by one replay validation property.

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
                **({} if validation_family is None else {'validation_family': validation_family}),
                **({} if requires_replay_cache is None else {'requires_replay_cache': requires_replay_cache}),
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )
