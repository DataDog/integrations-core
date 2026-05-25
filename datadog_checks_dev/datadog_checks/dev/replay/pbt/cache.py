# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from datadog_checks.dev.replay.pbt.openmetrics import mutate_body_label_order


def copy_replay_cache(source: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)
    return destination


def _request_capture_files(cache_dir: Path) -> list[Path]:
    manifest_path = cache_dir / 'capture.json'
    manifest = json.loads(manifest_path.read_text())
    if isinstance(manifest, dict):
        files = manifest.get('files', {})
        requests_file = files.get('requests') if isinstance(files, dict) else None
        if requests_file:
            return [cache_dir / str(requests_file)]
        return []
    if isinstance(manifest, list):
        return [manifest_path]
    return []


def mutate_request_capture_label_order(cache_dir: Path) -> int:
    """Sort labels in OpenMetrics response bodies for request replay captures.

    Returns the number of HTTP records whose body changed. Unsupported capture
    shapes or unsupported body lines are preserved unchanged.
    """
    changed_records = 0
    for capture_file in _request_capture_files(cache_dir):
        records: Any = json.loads(capture_file.read_text())
        if not isinstance(records, list):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue
            body = record.get('body')
            if not isinstance(body, str):
                continue
            mutated_body = mutate_body_label_order(body)
            if mutated_body != body:
                record['body'] = mutated_body
                changed_records += 1

        capture_file.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    return changed_records
