# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.process import ProcessCheck

from . import common


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
