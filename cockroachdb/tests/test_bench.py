# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.cockroachdb import CockroachdbCheck

pytestmark = [pytest.mark.usefixtures('dd_environment')]


def test_run(benchmark, dd_run_check, instance):
    check = CockroachdbCheck('cockroachdb', {}, [instance])

    # Run once to get instantiation of config out of the way.
    dd_run_check(check)

    benchmark(dd_run_check, check)
