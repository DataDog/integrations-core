# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import time

import psycopg2
import pytest

from .common import (
    DB_NAME,
    HOST,
    assert_metric_at_least,
    check_bgw_metrics,
    check_common_metrics,
    check_connection_metrics,
    check_db_count,
    check_replication_delay,
    check_slru_metrics,
    check_wal_receiver_count_metrics,
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
    check_wal_receiver_count_metrics(aggregator, expected_tags=expected_tags, value=1)

    aggregator.assert_all_metrics_covered()


def test_wal_receiver_metrics(aggregator, integration_check, pg_replica_instance):
    check = integration_check(pg_replica_instance)
    expected_tags = pg_replica_instance['tags'] + ['port:{}'.format(pg_replica_instance['port']), 'status:streaming']
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            # Ask for a new txid to force a WAL change
            cur.execute('select txid_current();')
            cur.fetchall()
    # Wait for 100ms for WAL sender to send message
    time.sleep(0.1)

    check.check(pg_replica_instance)
    # All ages should have been updated within the last second
    assert_metric_at_least(
        aggregator,
        'postgresql.wal_receiver.last_msg_receipt_age',
        higher_bound=1,
        tags=expected_tags,
        count=1,
    )
    assert_metric_at_least(
        aggregator,
        'postgresql.wal_receiver.last_msg_receipt_age',
        higher_bound=1,
        tags=expected_tags,
        count=1,
    )
    assert_metric_at_least(
        aggregator,
        'postgresql.wal_receiver.latest_end_age',
        higher_bound=1,
        tags=expected_tags,
        count=1,
    )
