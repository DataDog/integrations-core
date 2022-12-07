# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.hyperv import HypervCheck


def test_refresh_counters(benchmark, instance_refresh, dd_run_check):
    check = HypervCheck('hyperv', {}, [instance_refresh])

    # Run once to get any PDH setup out of the way.
    dd_run_check(check)

    benchmark(check.check, instance_refresh)


def test_no_refresh_counters(benchmark, instance_no_refresh, dd_run_check):
    check = HypervCheck('hyperv', {}, [instance_no_refresh])

    # Run once to get any PDH setup out of the way.
    dd_run_check(check)

    benchmark(check.check, instance_no_refresh)
