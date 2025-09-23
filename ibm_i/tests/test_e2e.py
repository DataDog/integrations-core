# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.ibm_i import IbmICheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check("ibm_i.can_connect", IbmICheck.CRITICAL, tags=['foo:bar'])
