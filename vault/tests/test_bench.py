# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark, dd_run_check, check, instance):
    check = check(instance())

    # Run once to get instantiation of config out of the way.
    dd_run_check(check)

    benchmark(dd_run_check, check)
