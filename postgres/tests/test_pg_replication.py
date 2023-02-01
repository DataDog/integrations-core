# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from .common import (
    check_bgw_metrics,
    check_common_metrics,
    check_connection_metrics,
    check_db_count,
    check_replication_delay,
    check_slru_metrics,
    check_wal_receiver_metrics,
)

CONNECTION_METRICS = ['postgresql.max_connections', 'postgresql.percent_usage_connections']

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_common_replica_metrics(aggregator, integration_check, pg_replica_instance):
    check = integration_check(pg_replica_instance)
    check.check(pg_replica_instance)

    expected_tags = pg_replica_instance['tags'] + ['port:{}'.format(pg_replica_instance['port'])]
    check_common_metrics(aggregator, expected_tags=expected_tags)
    check_bgw_metrics(aggregator, expected_tags)
    check_connection_metrics(aggregator, expected_tags=expected_tags)
    check_db_count(aggregator, expected_tags=expected_tags)
    check_slru_metrics(aggregator, expected_tags=expected_tags)
    check_replication_delay(aggregator, expected_tags=expected_tags)
    check_wal_receiver_metrics(aggregator, expected_tags=expected_tags)

    aggregator.assert_all_metrics_covered()
