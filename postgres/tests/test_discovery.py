# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import os
import re
import time
from contextlib import contextmanager

import psycopg
import psycopg.sql
import pytest

from .common import HOST, PASSWORD_ADMIN, USER_ADMIN, _get_expected_tags, check_common_metrics
from .utils import requires_over_13, run_one_check
from datadog_checks.postgres.config_models.dict_defaults import instance_database_autodiscovery

DISCOVERY_CONFIG = {
    "enabled": True,
    "include": ["dogs_[0-9]"],
    "exclude": ["dogs_5$"],
}

POSTGRES_VERSION = os.environ.get('POSTGRES_VERSION', None)


# the number of test databases that exist from [dogs_0, dogs_9]
NUM_DOGS_DATABASES = 10

RELATION_METRICS = {
    'postgresql.seq_scans',
    'postgresql.seq_rows_read',
    'postgresql.rows_inserted',
    'postgresql.rows_updated',
    'postgresql.rows_deleted',
    'postgresql.rows_hot_updated',
    'postgresql.live_rows',
    'postgresql.dead_rows',
    'postgresql.heap_blocks_read',
    'postgresql.heap_blocks_hit',
    'postgresql.vacuumed',
    'postgresql.autovacuumed',
    'postgresql.analyzed',
    'postgresql.autoanalyzed',
}

DYNAMIC_RELATION_METRICS = {
    'postgresql.relation.pages',
    'postgresql.relation.tuples',
    'postgresql.relation.all_visible',
    'postgresql.table_size',
    'postgresql.relation_size',
    'postgresql.index_size',
    'postgresql.toast_size',
    'postgresql.total_size',
}

FUNCTION_METRICS = {
    'postgresql.function.calls',
    'postgresql.function.total_time',
    'postgresql.function.self_time',
}

COUNT_METRICS = {
    'postgresql.table.count',
}

CHECKSUM_METRICS = {
    'postgresql.checksums.checksum_failures',
}


@contextmanager
def get_postgres_connection(dbname="postgres"):
    conn_args = {'host': HOST, 'dbname': dbname, 'user': USER_ADMIN, 'password': PASSWORD_ADMIN}
    conn = psycopg.connect(**conn_args)
    conn.autocommit = True
    yield conn


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_autodiscovery_simple(integration_check, pg_instance):
    """
    Test simple autodiscovery.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"])
    assert len(databases) == expected_len


def test_autodiscovery_global_view_db_specified(integration_check, pg_instance):
    """
    Test autodiscovery with global view db specified.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance["database_autodiscovery"]["global_view_db"] = "dogs_0"
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"])
    assert len(databases) == expected_len


def test_autodiscovery_max_databases(integration_check, pg_instance):
    """
    Test database list truncation.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance['database_autodiscovery']['max_databases'] = 7
    del pg_instance['dbname']

    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    assert len(databases) == pg_instance['database_autodiscovery']['max_databases']
    expected_warning = [
        "Autodiscovery found {} databases, which was more than the specified limit of {}. "
        "Increase `max_databases` in the `database_autodiscovery` block of the agent configuration "
        "to see these extra databases. "
        "The database list will be truncated.\ncode=autodiscovered-databases-exceeds-limit max_databases={}".format(
            NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"]),
            pg_instance['database_autodiscovery']['max_databases'],
            pg_instance['database_autodiscovery']['max_databases'],
        )
    ]
    assert check.warnings == expected_warning


@requires_over_13
def test_autodiscovery_refresh(integration_check, pg_instance):
    """
    Test cache refresh by adding a database in the middle of a check.
    """
    database_to_find = "cats"

    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance['database_autodiscovery']['include'].append(database_to_find)
    del pg_instance['dbname']
    pg_instance["database_autodiscovery"]['refresh'] = 1
    check = integration_check(pg_instance)
    run_one_check(check, cancel=False)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"])
    assert len(databases) == expected_len

    with get_postgres_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(database_to_find)))

            time.sleep(pg_instance["database_autodiscovery"]['refresh'])
            databases = check.autodiscovery.get_items()
            assert len(databases) == expected_len + 1
        finally:
            # Need to drop the new database to clean up the environment for next tests.
            cursor.execute(
                psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE);").format(psycopg.sql.Identifier(database_to_find))
            )


@pytest.mark.flaky(max_runs=5)
def test_autodiscovery_collect_all_metrics(aggregator, integration_check, pg_instance):
    """
    Check that metrics get collected for each database discovered.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance["database_autodiscovery"]["include"] = ["dogs$", "dogs_noschema$", "dogs_nofunc$"]
    pg_instance['relations'] = [
        {'relation_regex': '.*'},
    ]
    pg_instance['collect_function_metrics'] = True
    pg_instance['collect_count_metrics'] = True
    pg_instance['collect_checksum_metrics'] = True
    del pg_instance['dbname']

    # execute dummy_function to populate pg_stat_user_functions for dogs_nofunc database
    # it does not make sense to create and execute the dummy_function for every single database
    with get_postgres_connection(dbname='dogs_nofunc') as conn:
        with conn.cursor() as cursor:
            # Run a few times to reduce flakiness
            cursor.execute("SELECT dummy_function()")
            cursor.execute("SELECT dummy_function()")
            cursor.execute("SELECT dummy_function()")
            cursor.execute("SELECT dummy_function()")
    conn.close()

    check = integration_check(pg_instance)
    check.check(pg_instance)

    # assert that for all databases found,
    # relation/function/count metrics were reported
    databases = check.autodiscovery.get_items()
    for db in databases:
        relation_metrics_expected_tags = _get_expected_tags(check, pg_instance, db=db, table='breed', schema='public')
        count_metrics_expected_tags = _get_expected_tags(check, pg_instance, db=db, schema='public')
        checksum_metrics_expected_tags = _get_expected_tags(check, pg_instance, db=db)
        for metric in RELATION_METRICS:
            aggregator.assert_metric(metric, tags=relation_metrics_expected_tags)
        for metric in DYNAMIC_RELATION_METRICS:
            aggregator.assert_metric(metric, tags=relation_metrics_expected_tags)
        for metric in COUNT_METRICS:
            aggregator.assert_metric(metric, tags=count_metrics_expected_tags)
        if float(POSTGRES_VERSION) >= 12:
            for metric in CHECKSUM_METRICS:
                aggregator.assert_metric(metric, tags=checksum_metrics_expected_tags)

    # we only created and executed the dummy_function in dogs_nofunc database
    for metric in FUNCTION_METRICS:
        aggregator.assert_metric(
            metric,
            tags=_get_expected_tags(check, pg_instance, db='dogs_nofunc', schema='public', function='dummy_function'),
        )

    aggregator.assert_metric(
        'dd.postgres._collect_relations_autodiscovery.time',
    )
    if float(POSTGRES_VERSION) >= 12:
        checksum_metrics_expected_tags = _get_expected_tags(check, pg_instance, with_db=False, enabled="true")
        aggregator.assert_metric('postgresql.checksums.enabled', value=1, tags=checksum_metrics_expected_tags)


def test_autodiscovery_exceeds_min_interval(aggregator, integration_check, pg_instance):
    """
    Check that relation metrics get collected for each database discovered.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance["database_autodiscovery"]["include"] = ["dogs$", "dogs_noschema$", "dogs_nofunc$"]
    pg_instance['min_collection_interval'] = 0.001
    del pg_instance['dbname']

    check = integration_check(pg_instance)
    check.check(pg_instance)

    assert len(check.warnings) == 1
    test_structure = re.compile(
        "Collecting metrics on autodiscovery metrics took .* ms, which is longer than "
        "the minimum collection interval. Consider increasing the min_collection_interval parameter "
        "in the postgres yaml configuration.\n"
    )
    assert test_structure.match(check.warnings[0])


def _set_allow_connection(dbname: str, allow: bool):
    with get_postgres_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            psycopg.sql.SQL("UPDATE pg_database SET datallowconn = %s WHERE datname = %s;"),
            (allow, dbname),
        )
        conn.commit()


def test_handle_cannot_connect(aggregator, integration_check, pg_instance):
    db_to_disable = "dogs_0"
    _set_allow_connection(db_to_disable, False)
    pg_instance["collect_settings"] = {"enabled": False}
    pg_instance["database_autodiscovery"] = {"enabled": True, "include": ["dogs_[0-3]"]}
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance)
    check_common_metrics(aggregator, expected_tags=expected_tags)
    _set_allow_connection(db_to_disable, True)


def test_database_autodiscovery_exclude_defaults(aggregator, integration_check, pg_instance):
    """
    Test that the exclude defaults for database autodiscovery filters the excluded databases
    """

    pg_instance["database_autodiscovery"] = {
        "enabled": True,
    }
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    databases_excluded_by_default = instance_database_autodiscovery().exclude
    check_excludes = check._config.database_autodiscovery.exclude 

    assert databases_excluded_by_default == check_excludes
    assert check.autodiscovery is not None


def test_database_autodiscovery_exclude_defaults_overrided(aggregator, integration_check, pg_instance):
    """
    Test that the exclude defaults for database autodiscovery can be overriden
    """

    excluded_db = "dogs_2"

    pg_instance["database_autodiscovery"] = {
        "enabled": True,
        "exclude": [f"{excluded_db}$"]
    }
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    databases = check.autodiscovery.get_items()

    assert check.autodiscovery is not None
    assert excluded_db not in databases
