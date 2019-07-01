# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests


@pytest.fixture(scope="function", autouse=True)
def setup_check():
    initialize_pdh_tests()
