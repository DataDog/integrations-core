# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck


def test_check(aggregator, agent_instance):
    check = CiliumCheck('cilium', {}, {})
    check.check(agent_instance)

    aggregator.assert_all_metrics_covered()


def test_generate_instance_agent(agent_instance):
    check = CiliumCheck('cilium', {}, agent_instance)
