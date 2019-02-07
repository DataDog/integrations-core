# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401


@pytest.fixture(scope="function", autouse=True)
def setup_check():
    initialize_pdh_tests()
