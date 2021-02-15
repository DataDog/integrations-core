# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from . import common


@pytest.mark.e2e
def test_varnish_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    for mname in common.COMMON_METRICS:
        aggregator.assert_metric(mname, tags=['cluster:webs', 'varnish_name:default'])
