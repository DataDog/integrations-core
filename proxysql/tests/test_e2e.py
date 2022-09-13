# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .conftest import _assert_all_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    _assert_all_metrics(aggregator)
