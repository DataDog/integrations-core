# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck


def test_check(aggregator, agent_instance, mock_agent_data):
    c = CiliumCheck('cilium', {}, [agent_instance])

    c.check(agent_instance)
