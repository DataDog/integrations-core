import pytest

from datadog_checks.postgres.settings import PG_STAT_STATEMENTS_MAX, TRACK_ACTIVITY_QUERY_SIZE


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = False
    return pg_instance


def test_settings_init(integration_check, dbm_instance):
    check = integration_check(dbm_instance)
    check.pg_settings = {}

    assert check.pg_settings.get(PG_STAT_STATEMENTS_MAX) is None
    assert check.pg_settings.get(TRACK_ACTIVITY_QUERY_SIZE) is None
    check.check(dbm_instance)
    assert check.pg_settings.get(PG_STAT_STATEMENTS_MAX) is not None
    assert check.pg_settings.get(TRACK_ACTIVITY_QUERY_SIZE) is not None


def test_settings_monitor(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    assert check.monitor_settings.pg_stat_statements_count is None
    check.monitor_settings.query([])
    assert check.monitor_settings.pg_stat_statements_count is not None
