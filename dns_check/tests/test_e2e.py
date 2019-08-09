# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check(deepcopy(common.INSTANCE_INTEGRATION))

    aggregator.assert_metric('dns.response_time')
