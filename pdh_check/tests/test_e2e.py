# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import pytest
from common import INSTANCE
from datadog_test_libs.win.pdh_mocks import initialize_pdh_tests, pdh_mocks_fixture  # noqa: F401


@pytest.mark.e2e
@pytest.mark.usefixtures('pdh_mocks_fixture')
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(INSTANCE))

    aggregator.assert_all_metrics_covered()
