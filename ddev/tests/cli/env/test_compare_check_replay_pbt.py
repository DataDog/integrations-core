# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from datadog_checks.dev.replay.pbt.cache import copy_replay_cache, mutate_request_capture_label_order


def _replay_pbt_settings() -> tuple[str, str, Path, str]:
    integration = os.environ.get('DDEV_REPLAY_PBT_INTEGRATION')
    environment = os.environ.get('DDEV_REPLAY_PBT_ENVIRONMENT')
    cache = os.environ.get('DDEV_REPLAY_PBT_CACHE')
    ref = os.environ.get('DDEV_REPLAY_PBT_REF', 'HEAD')
    if not integration or not environment or not cache:
        pytest.skip(
            'Set DDEV_REPLAY_PBT_INTEGRATION, DDEV_REPLAY_PBT_ENVIRONMENT, and DDEV_REPLAY_PBT_CACHE '
            'to run cached integration replay PBT.'
        )
    return integration, environment, Path(cache), ref


def _run_compare_check_cache(
    *,
    integration: str,
    environment: str,
    cache: Path,
    ref: str,
    artifacts: Path,
) -> dict:
    ddev_executable = Path(sys.executable).with_name('ddev')
    command = [
        str(ddev_executable),
        '--no-interactive',
        'env',
        'compare-check',
        integration,
        environment,
        '--old-ref',
        ref,
        '--new-ref',
        ref,
        '--replay-cache',
        str(cache),
        '--artifacts',
        str(artifacts),
        '--exact-artifacts-dir',
        '--overwrite',
    ]
    result = subprocess.run(command, cwd=Path.cwd(), text=True, capture_output=True)
    assert result.returncode == 0, f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    return json.loads((artifacts / 'diff.json').read_text())


def test_cached_replay_is_deterministic_for_same_ref(tmp_path):
    integration, environment, cache, ref = _replay_pbt_settings()

    first = tmp_path / 'first'
    second = tmp_path / 'second'
    first_diff = _run_compare_check_cache(
        integration=integration,
        environment=environment,
        cache=cache,
        ref=ref,
        artifacts=first,
    )
    second_diff = _run_compare_check_cache(
        integration=integration,
        environment=environment,
        cache=cache,
        ref=ref,
        artifacts=second,
    )

    assert first_diff['changed'] is False
    assert second_diff['changed'] is False
    assert json.loads((first / 'new.normalized.json').read_text()) == json.loads(
        (second / 'new.normalized.json').read_text()
    )


def test_label_order_mutated_cache_matches_original_output(tmp_path):
    integration, environment, cache, ref = _replay_pbt_settings()
    mutated_cache = copy_replay_cache(cache, tmp_path / 'mutated-cache')
    changed_records = mutate_request_capture_label_order(mutated_cache)
    if changed_records == 0:
        pytest.skip('Replay cache has no request records with reorderable OpenMetrics labels.')

    original = tmp_path / 'original'
    mutated = tmp_path / 'mutated'
    original_diff = _run_compare_check_cache(
        integration=integration,
        environment=environment,
        cache=cache,
        ref=ref,
        artifacts=original,
    )
    mutated_diff = _run_compare_check_cache(
        integration=integration,
        environment=environment,
        cache=mutated_cache,
        ref=ref,
        artifacts=mutated,
    )

    assert original_diff['changed'] is False
    assert mutated_diff['changed'] is False
    assert json.loads((original / 'new.normalized.json').read_text()) == json.loads(
        (mutated / 'new.normalized.json').read_text()
    )
