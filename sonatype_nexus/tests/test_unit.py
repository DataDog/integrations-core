# # (C) Datadog, Inc. 2024-present
# # All rights reserved
# # Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.sonatype_nexus import SonatypeNexusCheck


@pytest.mark.integration
def test_instance_check(dd_run_check, aggregator, instance):
    check = SonatypeNexusCheck("sonatype_nexus", {}, [instance])

    assert isinstance(check, AgentCheck)