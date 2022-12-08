# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from .common import POSTGRES_VERSION

from datadog_checks.postgres.util import SLRU_METRICS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.skipif(
    POSTGRES_VERSION is None or float(POSTGRES_VERSION) < 13.0,
    reason='SLRU test requires version 13.0 or higher (make sure POSTGRES_VERSION is set)',
)
def test_slru_metrics(aggregator, integration_check, pg_instance):
    pg_instance['collect_slru_metrics'] = True

    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    slru_caches = ['Subtrans', 'Serial', 'MultiXactMember', 'Xact', 'other', 'Notify', 'CommitTs', 'MultiXactOffset']
    expected_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
    ]

    for (metric_name, _) in SLRU_METRICS['metrics'].values():
        for slru_cache in slru_caches:
            aggregator.assert_metric(metric_name, count=1, tags=expected_tags + ['slru_name:{}'.format(slru_cache)])
