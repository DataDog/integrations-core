# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from .common import get_nexus_password

@pytest.mark.e2e
def test_e2e(dd_agent_check, instance, aggregator):
    instance["password"] = get_nexus_password()
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_metric('sonatype_nexus.status.available_cpus_health', value=1)
