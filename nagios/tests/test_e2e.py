# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

LOGGER = logging.getLogger(__name__)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    # This integration is based on tailing logs but because there is an agent running
    # there is an agent running in the agent image we cannot guarantee that we will
    # pick specific metrics on a test.
    # The test will fail if the integration cannot read nagios config or related files
    dd_agent_check(instance, rate=True)
