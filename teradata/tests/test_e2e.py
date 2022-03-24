# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.teradata import TeradataCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    with pytest.raises(Exception):
        aggregator = dd_agent_check(instance)
        expected_tags = ['teradata_server:localhost:1025']
        aggregator.assert_service_check('teradata.can_connect', TeradataCheck.CRITICAL, tags=expected_tags)
        aggregator.assert_service_check('teradata.can_query', TeradataCheck.CRITICAL, tags=expected_tags)
