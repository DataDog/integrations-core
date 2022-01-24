# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import AGENT_V2_METRICS, ON_CI, requires_new_environment

pytestmark = [requires_new_environment]


@pytest.mark.skipif(ON_CI, reason="This test environment flakes on CI")
@pytest.mark.e2e
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric in AGENT_V2_METRICS:
        aggregator.assert_metric(metric)
