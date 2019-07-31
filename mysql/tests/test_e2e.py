# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.mysql import MySql
from . import tags, variables


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance_basic):
    aggregator = dd_agent_check(instance_basic, rate=True)

    # Test service check
    aggregator.assert_service_check('mysql.can_connect', status=MySql.OK, tags=tags.SC_TAGS_MIN, count=2)

    # Test metrics
    testable_metrics = (
            variables.STATUS_VARS
            + variables.VARIABLES_VARS
            + variables.INNODB_VARS
            + variables.BINLOG_VARS
            + variables.SYSTEM_METRICS
            + variables.SYNTHETIC_VARS
    )

    for mname in testable_metrics:
        aggregator.assert_metric(mname, at_least=0)

    aggregator.assert_all_metrics_covered()
