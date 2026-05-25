# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Integration-level replay PBT driven by `ddev env replay-pbt`.

These tests are the real integration checks for replay-PBT: they take an
adapter-saved compare-check cache, run the target integration through cached
replay, optionally mutate the cache, and assert properties over normalized check
output. The CLI command supplies the target/cache through a JSON config file
so this file remains normal pytest/Hypothesis code with reproducible artifacts.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from datadog_checks.dev.replay.pbt.cache import copy_replay_cache, mutate_request_capture_label_order
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ddev.replay_pbt.properties import REPLAY_PBT_PROPERTY_CHOICES, ReplayPBTProperty


class ReplayPBTContext:
    def __init__(self, config: dict) -> None:
        self.integration = config['integration']
        self.environment = config['environment']
        self.cache = Path(config['replay_cache'])
        self.ref = config.get('ref') or 'HEAD'
        self.properties = set(config.get('properties') or REPLAY_PBT_PROPERTY_CHOICES)
        self.artifacts = Path(config['artifacts'])
        self.check_class = config.get('check_class')
        self.old_env = config.get('old_env')
        self.new_env = config.get('new_env')


@pytest.fixture(scope='session')
def replay_pbt_context(pytestconfig) -> ReplayPBTContext:
    config_path = pytestconfig.getoption('--replay-pbt-config')
    if not config_path:
        pytest.skip('Pass --replay-pbt-config or run through `ddev env replay-pbt`.')
    return ReplayPBTContext(json.loads(Path(config_path).read_text()))


def _skip_unselected(context: ReplayPBTContext, property_name: str) -> None:
    if property_name not in context.properties:
        pytest.skip(f'{property_name} was not selected for this replay-pbt run.')


def _run_compare_check_cache(
    *,
    context: ReplayPBTContext,
    cache: Path | str,
    artifacts: Path,
) -> dict:
    ddev_executable = Path(sys.executable).with_name('ddev')
    command = [
        str(ddev_executable),
        '--no-interactive',
        'env',
        'compare-check',
        context.integration,
        context.environment,
        '--old-ref',
        context.ref,
        '--new-ref',
        context.ref,
        '--replay-cache',
        str(cache),
        '--artifacts',
        str(artifacts),
        '--exact-artifacts-dir',
        '--overwrite',
    ]
    if context.check_class:
        command.extend(['--check-class', context.check_class])
    if context.old_env:
        command.extend(['--old-env', context.old_env])
    if context.new_env:
        command.extend(['--new-env', context.new_env])

    result = subprocess.run(command, cwd=Path.cwd(), text=True, capture_output=True)
    assert result.returncode == 0, f'stdout:\n{result.stdout}\nstderr:\n{result.stderr}'
    return json.loads((artifacts / 'diff.json').read_text())


def _read_normalized(run_dir: Path) -> dict:
    return json.loads((run_dir / 'new.normalized.json').read_text())


def test_cached_replay_is_deterministic_for_same_ref(replay_pbt_context: ReplayPBTContext):
    # Determinism property: replaying the same cached fixture through the same
    # integration ref twice should produce identical normalized output. The
    # first compare-check run also materializes `auto`/`latest` caches into an
    # exact artifact directory; the second run replays that materialized cache so
    # this catches nondeterminism in check execution, replay adapters,
    # normalization, and compare-check artifact regeneration.
    _skip_unselected(replay_pbt_context, ReplayPBTProperty.DETERMINISTIC)

    first = replay_pbt_context.artifacts / ReplayPBTProperty.DETERMINISTIC / 'first'
    second = replay_pbt_context.artifacts / ReplayPBTProperty.DETERMINISTIC / 'second'
    first_diff = _run_compare_check_cache(context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=first)
    second_diff = _run_compare_check_cache(context=replay_pbt_context, cache=first, artifacts=second)

    assert first_diff['changed'] is False
    assert second_diff['changed'] is False
    assert _read_normalized(first) == _read_normalized(second)


@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(mutation=st.sampled_from(['sort-openmetrics-labels']))
def test_label_order_mutated_cache_matches_original_output(replay_pbt_context: ReplayPBTContext, mutation: str):
    # Metamorphic OpenMetrics property: label order in a Prometheus/OpenMetrics
    # sample is not semantically meaningful, so sorting labels inside captured
    # request bodies should not change normalized Datadog check output. This
    # test copies the replay cache, applies that mutation to adapter-saved
    # request fixtures, then runs the real integration check against original and
    # mutated caches and compares normalized outputs.
    _skip_unselected(replay_pbt_context, ReplayPBTProperty.OPENMETRICS_LABEL_ORDER)
    assert mutation == 'sort-openmetrics-labels'

    property_dir = replay_pbt_context.artifacts / ReplayPBTProperty.OPENMETRICS_LABEL_ORDER
    original = property_dir / 'original'
    mutated = property_dir / 'mutated'
    mutated_cache = copy_replay_cache(replay_pbt_context.cache, property_dir / 'mutated-cache')
    changed_records = mutate_request_capture_label_order(mutated_cache)
    if changed_records == 0:
        pytest.skip('Replay cache has no request records with reorderable OpenMetrics labels.')

    original_diff = _run_compare_check_cache(
        context=replay_pbt_context, cache=replay_pbt_context.cache, artifacts=original
    )
    mutated_diff = _run_compare_check_cache(context=replay_pbt_context, cache=mutated_cache, artifacts=mutated)

    assert original_diff['changed'] is False
    assert mutated_diff['changed'] is False
    assert _read_normalized(original) == _read_normalized(mutated)
