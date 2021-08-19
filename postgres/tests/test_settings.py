import pytest

from datadog_checks.postgres.settings import (
    PG_STAT_STATEMENTS_MAX,
    PG_STAT_STATEMENTS_MAX_UNKNOWN_VALUE,
    TRACK_ACTIVITY_QUERY_SIZE,
    TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE,
)


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    return pg_instance


def test_settings_init(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    # test defaults before init
    assert check.pg_settings.settings[PG_STAT_STATEMENTS_MAX]['value'] == PG_STAT_STATEMENTS_MAX_UNKNOWN_VALUE
    assert check.pg_settings.settings[TRACK_ACTIVITY_QUERY_SIZE]['value'] == TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE

    # check invokes settings because `dbm` is enabled
    check.check(dbm_instance)
    assert check.pg_settings.settings[PG_STAT_STATEMENTS_MAX]['value'] != PG_STAT_STATEMENTS_MAX_UNKNOWN_VALUE
    assert check.pg_settings.settings[TRACK_ACTIVITY_QUERY_SIZE]['value'] != TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE


def test_settings_queries_tracked_values(integration_check, dbm_instance):
    dbm_instance['dbm'] = False
    check = integration_check(dbm_instance)

    assert check.pg_settings.settings[PG_STAT_STATEMENTS_MAX]['tracked_value'] is None
    assert check.pg_settings.settings[TRACK_ACTIVITY_QUERY_SIZE]['tracked_value'] is None

    check.pg_settings.query_settings([])

    assert check.pg_settings.settings[PG_STAT_STATEMENTS_MAX]['tracked_value'] is not None
    assert check.pg_settings.settings[TRACK_ACTIVITY_QUERY_SIZE]['tracked_value'] is None
