# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, realtime_instance):
    with pytest.raises(Exception):
        dd_agent_check(realtime_instance)
    vcenter_tag = ['vcenter_server:' + realtime_instance.get('host')]
    aggregator.assert_service_check("vsphere.can_connect", AgentCheck.CRITICAL, tags=vcenter_tag)
