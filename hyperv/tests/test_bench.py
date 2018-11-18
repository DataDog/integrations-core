# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.hyperv import HypervCheck


def test_run(benchmark, instance):
    check = HypervCheck('hyperv', {}, {}, [instance])

    # Run once to get any PDH setup out of the way.
    check.check(instance)

    benchmark(check.check, instance)
