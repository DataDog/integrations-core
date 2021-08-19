from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.postgres.settings import (
    PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE,
    TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE,
)

from .common import HOST, PORT


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    # make sure we shut down any orphaned threads and create a new Executor for each test
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['query_settings'] = {'monitor_settings': True, 'run_sync': True, 'collection_interval': 1}
    return pg_instance


def _expected_dbm_instance_tags(dbm_instance):
    return dbm_instance['tags'] + [
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:{}'.format(dbm_instance['dbname']),
    ]


@pytest.mark.parametrize("monitor_settings", [True, False])
def test_settings_async_job_enabled(integration_check, dbm_instance, monitor_settings):
    dbm_instance['query_settings'] = {'monitor_settings': monitor_settings, 'run_sync': False}
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    check.cancel()

    if monitor_settings:
        assert check.pg_settings._job_loop_future is not None
        check.pg_settings._job_loop_future.result()
    else:
        assert check.pg_settings._job_loop_future is None


def test_settings_async_job_inactive_stop(aggregator, integration_check, dbm_instance):
    dbm_instance['query_settings']['run_sync'] = False
    check = integration_check(dbm_instance)
    check.check(dbm_instance)

    # wait for it to stop and make sure it doesn't throw any exceptions
    check.pg_settings._job_loop_future.result()

    aggregator.assert_metric(
        "dd.postgres.async_job.inactive_stop",
        tags=_expected_dbm_instance_tags(dbm_instance) + ['job:query-settings'],
    )


def test_settings_async_job_cancel_cancel(aggregator, integration_check, dbm_instance):
    dbm_instance['query_settings']['run_sync'] = False
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    check.cancel()

    # wait for it to stop and make sure it doesn't throw any exceptions
    check.pg_settings._job_loop_future.result()

    assert not check.pg_settings._job_loop_future.running(), "settings thread should be stopped"
    assert check._db_pool.get(dbm_instance['dbname']) is None, "db connection should be gone"
    aggregator.assert_metric(
        "dd.postgres.async_job.cancel",
        tags=_expected_dbm_instance_tags(dbm_instance) + ['job:query-settings'],
    )


def test_settings_init(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    # test defaults before init
    assert check.pg_settings.pg_stat_statements_max.get_value() == PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE
    assert check.pg_settings.track_activity_query_size.get_value() == TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE

    # check invokes settings init because `dbm` is enabled
    check.check(dbm_instance)
    assert check.pg_settings.pg_stat_statements_max.get_value() != PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE
    assert check.pg_settings.track_activity_query_size.get_value() != TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE


def test_settings_init_with_error(aggregator, integration_check, dbm_instance):
    dbm_instance["dbm"] = False
    check = integration_check(dbm_instance)
    check.pg_settings._db = check._get_db("postgres")
    check._close_db_pool()  # break init
    check.pg_settings.init([])

    # ensure that we emit some sort of settings error metric from a failed init
    assert len(aggregator.metrics("dd.postgres.settings.error")) != 0


def test_settings_tracked_value_with_monitor_disabled(integration_check, dbm_instance):
    dbm_instance['query_settings']['monitor_settings'] = False

    check = integration_check(dbm_instance)
    check.check(dbm_instance)

    # ensure that the settings are loaded despite not monitoring their tracked values
    assert check.pg_settings.pg_stat_statements_max.get_value() != PG_STAT_STATMENTS_MAX_UNKNOWN_VALUE
    assert check.pg_settings.track_activity_query_size.get_value() != TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE

    assert check.pg_settings.pg_stat_statements_max.get_tracked_value() is None


def test_settings_tracked_value_with_monitor_enabled(aggregator, integration_check, dbm_instance):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    assert check.pg_settings.pg_stat_statements_max.get_tracked_value() is not None
    # ensure that a metric to keep track of tracked setting value is emitted
    assert len(aggregator.metrics("dd.postgres.settings.pg_stat_statements.max")) != 0
