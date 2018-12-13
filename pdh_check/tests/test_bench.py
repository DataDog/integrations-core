# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pdh_check import PDHCheck
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_cache(benchmark):
    initialize_pdh_tests()
    instance = {
        'cache_counter_instances': True,
        'countersetname': 'System',
        'metrics': [
            ['File Read Operations/sec', 'pdh.system.file_read_per_sec', 'gauge'],
            ['File Write Bytes/sec', 'pdh.system.file_write_bytes_sec', 'gauge'],
        ],
    }
    check = PDHCheck('pdh_check', {}, {}, [instance])

    # Run once to get any PDH setup out of the way.
    check.check(instance)

    benchmark(check.check, instance)


@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_no_cache(benchmark):
    initialize_pdh_tests()
    instance = {
        'cache_counter_instances': False,
        'countersetname': 'System',
        'metrics': [
            ['File Read Operations/sec', 'pdh.system.file_read_per_sec', 'gauge'],
            ['File Write Bytes/sec', 'pdh.system.file_write_bytes_sec', 'gauge'],
        ],
    }
    check = PDHCheck('pdh_check', {}, {}, [instance])

    # Run once to get any PDH setup out of the way.
    check.check(instance)

    benchmark(check.check, instance)
