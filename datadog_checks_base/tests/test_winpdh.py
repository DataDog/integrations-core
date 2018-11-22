# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import datadog_checks.stubs.datadog_agent as logger
from collections import defaultdict
from datadog_checks.stubs import aggregator

try:
    from datadog_checks.checks.win.winpdh import WinPDHCounter, SINGLE_INSTANCE_KEY

    # for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
    # it's used below.  noqa to suppress that error.
    from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401
    from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture_bad_perf_strings  # noqa: F401

except:  # noqa: E722
    import platform

    if platform.system() != 'Windows':
        pass

from .utils import requires_windows


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


'''
WinPDHCounter tests.

Test specific behavior of the WinPDHCounter class, which provides
the interface to the OS API.
'''


@requires_windows  # noqa: F811
def test_winpdhcounter_bad_strings_english(pdh_mocks_fixture_bad_perf_strings):
    initialize_pdh_tests()
    counter = WinPDHCounter('System', 'Processor Queue Length', logger)

    vals = counter.get_all_values()
    assert len(vals) == 1  # single instance key, should only have one value
    assert SINGLE_INSTANCE_KEY in vals


@requires_windows  # noqa: F811
def test_winpdhcounter_throws_on_bad_input(pdh_mocks_fixture):
    initialize_pdh_tests()
    with pytest.raises(AttributeError):
        WinPDHCounter('Ssystem', 'Processor Queue Length', logger)

    with pytest.raises(AttributeError):
        WinPDHCounter('System', 'PProcessor Queue Length', logger)


@requires_windows  # noqa: F811
def test_winpdhcounter_throws_on_bad_input_with_bad_strings(pdh_mocks_fixture_bad_perf_strings):
    initialize_pdh_tests()
    with pytest.raises(AttributeError):
        WinPDHCounter('Ssystem', 'Processor Queue Length', logger)

    with pytest.raises(AttributeError):
        WinPDHCounter('System', 'PProcessor Queue Length', logger)


@requires_windows  # noqa: F811
def test_winpdhcounter_bad_strings_not_english(pdh_mocks_fixture_bad_perf_strings):
    WinPDHCounter._use_en_counter_names = False
    WinPDHCounter.pdh_counter_dict = defaultdict(list)

    initialize_pdh_tests(lang="se-sv")
    '''
    expectation is that the initialization will fail.  We attempt to fall
    back to english counters if the strings database isn't present; however,
    on non-english windows the english counters won't work
    '''
    with pytest.raises(AttributeError):
        WinPDHCounter('System', 'Processor Queue Length', logger)


@requires_windows  # noqa: F811
def test_winpdhcounter_non_english(pdh_mocks_fixture):
    WinPDHCounter._use_en_counter_names = False
    WinPDHCounter.pdh_counter_dict = defaultdict(list)
    initialize_pdh_tests(lang="se-sv")
    counter = WinPDHCounter('System', 'Processor Queue Length', logger)

    vals = counter.get_all_values()
    assert len(vals) == 1  # single instance key, should only have one value
    assert SINGLE_INSTANCE_KEY in vals
