# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.iis import IIS


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_cache(benchmark):
    instance = {
        'cache_counter_instances': True,
        'host': '.',
    }
    check = IIS('iis', {}, {}, [instance])

    # Run once to get any PDH setup out of the way.
    check.check(instance)

    benchmark(check.check, instance)


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_no_cache(benchmark):
    instance = {
        'cache_counter_instances': False,
        'host': '.',
    }
    check = IIS('iis', {}, {}, [instance])

    # Run once to get any PDH setup out of the way.
    check.check(instance)

    benchmark(check.check, instance)
