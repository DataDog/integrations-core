# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gc
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.agent.memory import MemoryProfileMetric, profile_memory


def test_concurrent_profile_memory_calls_execute_without_interference():
    owner_started = threading.Event()
    contender_finished = threading.Event()
    calls = []

    def run_owner() -> list[MemoryProfileMetric]:
        def owner_work() -> None:
            calls.append('owner')
            owner_started.set()
            assert contender_finished.wait(timeout=5)

        return profile_memory(owner_work, {})

    def run_contender() -> list[MemoryProfileMetric]:
        assert owner_started.wait(timeout=5)
        try:
            return profile_memory(lambda: calls.append('contender'), {})
        finally:
            contender_finished.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        owner = executor.submit(run_owner)
        contender = executor.submit(run_contender)

    assert len(owner.result()) == 1
    assert contender.result() == []
    assert calls.count('owner') == 1
    assert calls.count('contender') == 1


def test_nested_profile_memory_call_executes_without_interference():
    calls = []
    nested_metrics = None

    def outer_work() -> None:
        nonlocal nested_metrics
        calls.append('outer')
        nested_metrics = profile_memory(lambda: calls.append('nested'), {})

    metrics = profile_memory(outer_work, {})

    assert len(metrics) == 1
    assert nested_metrics == []
    assert calls.count('outer') == 1
    assert calls.count('nested') == 1


@pytest.mark.parametrize('gc_enabled', [True, False])
def test_profile_memory_restores_gc_state(gc_enabled):
    original_gc_enabled = gc.isenabled()
    if gc_enabled:
        gc.enable()
    else:
        gc.disable()

    try:
        profile_memory(lambda: None, {})

        assert gc.isenabled() is gc_enabled
    finally:
        if original_gc_enabled:
            gc.enable()
        else:
            gc.disable()
