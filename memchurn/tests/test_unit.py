# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Callable

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.memchurn import MemChurnCheck

CORE_METRICS = [
    'memchurn.workers',
    'memchurn.retained_bytes',
    'memchurn.live_bytes',
    'memchurn.alloc_calls_last_run',
    'memchurn.free_calls_last_run',
]


def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
) -> None:
    check = MemChurnCheck('memchurn', {}, [instance])
    try:
        dd_run_check(check)
    finally:
        check.cancel()

    for metric in CORE_METRICS:
        aggregator.assert_metric(metric, count=1)
    aggregator.assert_metric('memchurn.workers', value=instance['num_workers'])

    # Every emitted metric is declared in metadata.csv with the correct type and unit.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_pool_is_built_once(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
) -> None:
    check = MemChurnCheck('memchurn', {}, [instance])
    try:
        dd_run_check(check)
        first_pool = list(check._workers)
        dd_run_check(check)
        second_pool = list(check._workers)
    finally:
        check.cancel()

    assert len(first_pool) == instance['num_workers']
    # The same worker objects persist across runs; the pool is never rebuilt.
    assert first_pool == second_pool


def test_allocation_activity(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
) -> None:
    check = MemChurnCheck('memchurn', {}, [instance])
    try:
        dd_run_check(check)
    finally:
        check.cancel()

    alloc_calls = aggregator.metrics('memchurn.alloc_calls_last_run')[0].value
    assert alloc_calls > 0


def test_draw_size_respects_bounds(instance: InstanceType) -> None:
    check = MemChurnCheck('memchurn', {}, [instance])
    try:
        sizes = [check.draw_size() for _ in range(5000)]
    finally:
        check.cancel()

    assert all(instance['min_alloc_bytes'] <= s <= instance['max_alloc_bytes'] for s in sizes)
    # The distribution has a long tail: some draws land in the upper decile.
    tail_threshold = instance['max_alloc_bytes'] // 2
    assert any(s >= tail_threshold for s in sizes)


def test_degrades_without_libc(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
) -> None:
    check = MemChurnCheck('memchurn', {}, [instance])
    check.libc = None  # simulate a non-glibc platform where the malloc lookup failed
    try:
        dd_run_check(check)
    finally:
        check.cancel()

    aggregator.assert_metric('memchurn.workers', value=0, count=1)
    assert not check._workers
