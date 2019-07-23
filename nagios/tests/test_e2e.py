# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

LOGGER = logging.getLogger(__name__)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    dd_agent_check(instance, rate=True)
