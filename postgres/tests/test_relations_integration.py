# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from .utils import requires_over_12
from datadog_checks.postgres.relationsmanager import QUERY_TABLE_STATISTICS
from .common import _get_expected_tags


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@requires_over_12
def test_autodiscovery_collect_table_statistic_metrics(aggregator, integration_check, pg_instance):
    """
    Check that metrics get collected for each database discovered.
    """
    pg_instance['relations'] = ['public.breed']

    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_metrics = [q for q in QUERY_TABLE_STATISTICS['metrics'].keys()]

    for metric in expected_metrics:
        aggregator.assert_metric(
            metric,
            tags=_get_expected_tags(check, pg_instance, db='dogs_nofunc', schema='public', function='dummy_function'),
        )

    aggregator.assert_metric(
        'dd.postgres._collect_relations_autodiscovery.time',
    )