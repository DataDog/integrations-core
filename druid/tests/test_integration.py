# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.druid import DruidCheck


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics(aggregator, pg_instance):
    check = DruidCheck('druid', {}, [pg_instance])
    check.check(pg_instance)

    aggregator.assert_all_metrics_covered()
