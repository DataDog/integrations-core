# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared test helpers.

Fixtures live in two directories and the split is deliberate:

``captured/``
    Verbatim responses recorded from the Cisco DevNet always-on sandbox. Real values.

``wireless_synthetic/``
    Access point and radio payloads. The *keys* are generated from Cisco's published OpenAPI
    schema and are checked against it by ``test_spec_conformance.py``. The *values* are
    hand-chosen, because Cisco's own schema examples are not physically plausible -- the
    example for ``RadioKpi.noise`` is ``10`` on a field documented in dBm, where a real noise
    floor is around -90. Never assert that a synthetic value matches a real controller.

Mutations are expressed as code via :func:`with_value`, never as hand-edited JSON, so that a
reviewer can always tell a recording from an alteration.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).parent / 'fixtures'
CAPTURED_DIR = FIXTURE_ROOT / 'captured'
WIRELESS_SYNTHETIC_DIR = FIXTURE_ROOT / 'wireless_synthetic'


def load_captured(name: str) -> Any:
    """Load a verbatim sandbox recording by file stem."""
    return json.loads((CAPTURED_DIR / f'{name}.json').read_text())


def load_wireless_synthetic(name: str) -> Any:
    """Load a synthetic access point payload by file stem."""
    return json.loads((WIRELESS_SYNTHETIC_DIR / f'{name}.json').read_text())


def metric_values(aggregator: Any, name: str, *required_tags: str) -> list[float]:
    """Values submitted for ``name`` on series carrying all of ``required_tags``.

    ``assert_metric(tags=...)`` matches the whole tag set, which makes a test fail whenever an
    unrelated tag is added. This asserts on containment instead, so a test states only the tags
    it actually cares about.
    """
    return [metric.value for metric in aggregator.metrics(name) if all(t in metric.tags for t in required_tags)]


def with_value(payload: Any, dotted_path: str, value: Any) -> Any:
    """Return a deep copy of ``payload`` with ``dotted_path`` set to ``value``.

    List indices are written as plain integers, so ``response.0.metricsDetails.cpuScore``
    addresses the first record. The original payload is never modified.

    Raises:
        KeyError: if an intermediate key does not exist, so that a typo in a test fails loudly
            instead of silently creating a new field.
    """
    result = copy.deepcopy(payload)
    cursor = result
    parts = dotted_path.split('.')
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    leaf = parts[-1]
    if isinstance(cursor, list):
        cursor[int(leaf)] = value
    else:
        if leaf not in cursor:
            raise KeyError(f'{dotted_path!r} does not exist in the payload; check for a typo')
        cursor[leaf] = value
    return result
