# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .utils import run_check


@pytest.mark.usefixtures('dd_environment')
def test_run(benchmark, check, instance):
    check = check(instance())

    # Run once to get instantiation of config out of the way.
    run_check(check)

    benchmark(run_check, check)
