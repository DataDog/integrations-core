# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from flaky import flaky

from datadog_checks.postgres.util import STAT_SUBSCRIPTION_METRICS

from .common import (
    _get_expected_tags,
    _iterate_metric_name,
    assert_metric_at_least,
    check_bgw_metrics,
    check_common_metrics,
    check_conflict_metrics,
    check_connection_metrics,
    check_control_metrics,
    check_db_count,
    check_file_wal_metrics,
    check_performance_metrics,
    check_slru_metrics,
    check_snapshot_txid_metrics,
    check_stat_wal_metrics,
    check_subscription_metrics,
    check_subscription_state_metrics,
    check_subscription_stats_metrics,
    check_uptime_metrics,
    check_wal_receiver_metrics,
)
from .utils import requires_over_10, requires_over_11, requires_over_14, requires_over_15

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@requires_over_11
@flaky(max_runs=5)
def test_common_logical_replica_metrics(aggregator, integration_check, pg_replica_logical):
    check = integration_check(pg_replica_logical)
    check._connect()
    check.initialize_is_aurora()
    check.check(pg_replica_logical)

    expected_tags = _get_expected_tags(check, pg_replica_logical)
    check_common_metrics(aggregator, expected_tags=expected_tags)
    check_bgw_metrics(aggregator, expected_tags)
    check_connection_metrics(aggregator, expected_tags=expected_tags)
    check_control_metrics(aggregator, expected_tags=expected_tags)
    check_db_count(aggregator, expected_tags=expected_tags)
    check_slru_metrics(aggregator, expected_tags=expected_tags)
    check_conflict_metrics(aggregator, expected_tags=expected_tags)
    check_uptime_metrics(aggregator, expected_tags=expected_tags)
    check_snapshot_txid_metrics(aggregator, expected_tags=expected_tags)
    check_stat_wal_metrics(aggregator, expected_tags=expected_tags)
    check_file_wal_metrics(aggregator, expected_tags=expected_tags)

    check_wal_receiver_metrics(aggregator, connected=False, expected_tags=expected_tags)
    check_subscription_metrics(aggregator, expected_tags=expected_tags + ['subscription_name:subscription_cities'])
    check_subscription_stats_metrics(
        aggregator, expected_tags=expected_tags + ['subscription_name:subscription_persons']
    )
    check_subscription_state_metrics(
        aggregator,
        expected_tags=expected_tags
        + ['subscription_name:subscription_persons', 'relation:persons_indexed', 'state:ready'],
    )

    check_performance_metrics(aggregator, expected_tags=check.debug_stats_kwargs()['tags'])

    aggregator.assert_all_metrics_covered()


@requires_over_15
def test_subscription_stats_apply_errors(aggregator, integration_check, pg_replica_logical):
    check = integration_check(pg_replica_logical)
    check.check(pg_replica_logical)
    # subscription_persons should have apply errors
    # select * from pg_stat_subscription_stats ;
    #  subid |        subname        | apply_error_count | sync_error_count | stats_reset
    # -------+-----------------------+-------------------+------------------+-------------
    #  16649 | subscription_persons  |                17 |                0 |
    #  16650 | subscription_cities   |                 0 |               16 |
    #  16651 | subscription_persons2 |                 0 |                0 |
    expected_subscription_tags = _get_expected_tags(check, pg_replica_logical, subscription_name='subscription_persons')
    assert_metric_at_least(
        aggregator,
        'postgresql.subscription.apply_error',
        lower_bound=1,
        tags=expected_subscription_tags,
        count=1,
    )


@requires_over_15
def test_subscription_stats_sync_errors(aggregator, integration_check, pg_replica_logical):
    check = integration_check(pg_replica_logical)
    # subscription_persons should have sync errors
    # select * from pg_stat_subscription_stats ;
    #  subid |        subname        | apply_error_count | sync_error_count | stats_reset
    # -------+-----------------------+-------------------+------------------+-------------
    #  16649 | subscription_persons  |                17 |                0 |
    #  16650 | subscription_cities   |                 0 |               16 |
    #  16651 | subscription_persons2 |                 0 |                0 |

    check.check(pg_replica_logical)
    expected_subscription_tags = _get_expected_tags(check, pg_replica_logical, subscription_name='subscription_cities')
    assert_metric_at_least(
        aggregator,
        'postgresql.subscription.sync_error',
        lower_bound=1,
        tags=expected_subscription_tags,
        count=1,
    )


@requires_over_10
def test_stat_subscription(aggregator, integration_check, pg_replica_logical):
    check = integration_check(pg_replica_logical)
    check.check(pg_replica_logical)
    # select * from pg_stat_subscription;
    #  subid |        subname        | pid | relid | received_lsn |      last_msg_send_time       |...
    # -------+-----------------------+-----+-------+--------------+-------------------------------+...
    #  16649 | subscription_persons  |     |       |              |                               |...
    #  16650 | subscription_cities   | 276 |       | 0/220954B0   | 2023-11-10 15:24:05.354626+00 |...
    #  16651 | subscription_persons2 |     |       |              |                               |...
    expected_subscription_tags = _get_expected_tags(check, pg_replica_logical, subscription_name='subscription_cities')

    # All age metrics should be reported
    for metric in _iterate_metric_name(STAT_SUBSCRIPTION_METRICS):
        assert_metric_at_least(
            aggregator,
            metric,
            lower_bound=0.001,
            tags=expected_subscription_tags,
            min_count=1,
            max_count=2,
        )


@requires_over_14
def test_subscription_state(aggregator, integration_check, pg_replica_logical):
    check = integration_check(pg_replica_logical)
    check.check(pg_replica_logical)
    #         subname        | srrelid         |   state
    # -----------------------+-----------------+-------------
    #  subscription_persons  | persons_indexed | ready
    #  subscription_persons2 | persons_indexed | initialize
    #  subscription_cities   | cities          | data_copied
    base_tags = _get_expected_tags(check, pg_replica_logical)
    expected_states = [
        ['subscription_name:subscription_persons', 'relation:persons_indexed', 'state:ready'],
        ['subscription_name:subscription_persons2', 'relation:persons_indexed', 'state:initialize'],
        ['subscription_name:subscription_cities', 'relation:cities', 'state:data_copy'],
    ]
    for state_tags in expected_states:
        aggregator.assert_metric('postgresql.subscription.state', value=1, count=1, tags=base_tags + state_tags)
