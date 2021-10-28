# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .conftest import _assert_all_metrics, _assert_metadata


@pytest.mark.e2e
def test_e2e(dd_agent_check, datadog_agent):
    aggregator = dd_agent_check(rate=True)
    _assert_metadata(datadog_agent, check_id='proxysql')
    _assert_all_metrics(aggregator)
