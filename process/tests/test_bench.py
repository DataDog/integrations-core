# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from unittest import mock

import psutil

from datadog_checks.process import ProcessCheck

from . import common

# Simulated pid count and per-call latency of a native bulk ppid_map snapshot on Windows,
# per https://github.com/DataDog/integrations-core/pull/25367#pullrequestreview-5344915174
SIMULATED_PID_COUNT = 400
SIMULATED_PPID_CALL_LATENCY = 0.008


class SlowMockProcess:
    """Stand-in for psutil.Process(pid) whose ppid() pays the simulated per-call cost."""

    def __init__(self, pid):
        self.pid = pid

    def ppid(self):
        time.sleep(SIMULATED_PPID_CALL_LATENCY)
        return 1


def _naive_get_child_processes(pids):
    # Reconstruction of the pre-fix implementation: Process(pid).ppid() called per system pid.
    ppid_map = {}
    for p in psutil.pids():
        try:
            ppid_map[p] = psutil.Process(p).ppid()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    children_pids = set()
    for pid in pids:
        for p, ppid in ppid_map.items():
            if ppid == pid:
                children_pids.add(p)
    return children_pids


def test_collect_children_naive_per_pid_loop(benchmark):
    # Simulates the pre-fix O(n^2) cost on a platform like Windows.
    simulated_pids = list(range(1, SIMULATED_PID_COUNT + 1))
    with (
        mock.patch('psutil.pids', return_value=simulated_pids),
        mock.patch('psutil.Process', side_effect=SlowMockProcess),
    ):
        benchmark.pedantic(_naive_get_child_processes, args=({1},), rounds=3, iterations=1)


def test_collect_children_fast_ppid_map(benchmark, monkeypatch):
    # The fixed implementation: a single native bulk ppid_map() call.
    simulated_ppid_map = dict.fromkeys(range(1, SIMULATED_PID_COUNT + 1), 1)

    def slow_ppid_map():
        time.sleep(SIMULATED_PPID_CALL_LATENCY)
        return simulated_ppid_map

    monkeypatch.setattr(psutil._psplatform, 'ppid_map', slow_ppid_map, raising=False)
    process = ProcessCheck(common.CHECK_NAME, {}, [{'name': 'foo', 'pid': 1, 'collect_children': True}])
    benchmark.pedantic(process._get_child_processes, args=({1},), rounds=5, iterations=1)


def test_run(benchmark, dd_run_check):
    instance = {
        'name': 'py',
        'search_string': ['python'],
        'exact_match': False,
        'ignored_denied_access': True,
        'use_oneshot': False,
        'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
    }
    process = ProcessCheck(common.CHECK_NAME, {}, [instance])
    dd_run_check(process)

    benchmark(dd_run_check, process)


def test_run_oneshot(benchmark, dd_run_check):
    instance = {
        'name': 'py',
        'search_string': ['python'],
        'exact_match': False,
        'ignored_denied_access': True,
        'use_oneshot': True,
        'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
    }
    process = ProcessCheck(common.CHECK_NAME, {}, [instance])
    dd_run_check(process)

    benchmark(dd_run_check, process)
