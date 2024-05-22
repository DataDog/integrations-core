# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    aggregator.assert_service_check('traefik_mesh.openmetrics.health', ServiceCheck.OK, count=2)
    aggregator.assert_service_check('traefik_mesh.controller.ready', ServiceCheck.OK, count=2)
