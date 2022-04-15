# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import SERVICE_CHECK_CONNECT, SERVICE_CHECK_QUERY


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    expected_tags = ['teradata_server:localhost:1025']

    with pytest.raises(Exception, match="ModuleNotFoundError: No module named 'teradatasql'"):
        aggregator = dd_agent_check(instance)
        aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, tags=expected_tags)
        aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, tags=expected_tags)
