# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator):
    aggregator = dd_agent_check()
    aggregator.assert_metric('sonatype_nexus.status.available_cpus_health', value=1)
