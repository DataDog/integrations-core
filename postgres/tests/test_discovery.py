# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import re
import time
from contextlib import contextmanager

import psycopg
import pytest
from psycopg import sql

from datadog_checks.base import ConfigurationError

from .common import HOST, PASSWORD_ADMIN, USER_ADMIN, _get_expected_tags
from .utils import requires_over_13, run_one_check

DISCOVERY_CONFIG = {
    "enabled": True,
    "include": ["dogs_([0-9]|[1-9][0-9]|10[0-9])"],
    "exclude": ["dogs_5$", "dogs_50$"],
}

# the number of test databases that exist from [dogs_0, dogs_100]
NUM_DOGS_DATABASES = 101

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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_simple(integration_check, pg_instance):
    """
    Test simple autodiscovery.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = ['pg_index']
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"])
    assert len(databases) == expected_len


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_max_databases(integration_check, pg_instance):
    """
    Test database list truncation.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance['database_autodiscovery']['max_databases'] = 20
    pg_instance['relations'] = ['pg_index']
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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@requires_over_13
def test_autodiscovery_refresh(integration_check, pg_instance):
    """
    Test cache refresh by adding a database in the middle of a check.
    """
    database_to_find = "cats"

    @contextmanager
    def get_postgres_connection():
        conn_args = {'host': HOST, 'dbname': "postgres", 'user': USER_ADMIN, 'password': PASSWORD_ADMIN}
        conn = psycopg.connect(**conn_args)
        conn.autocommit = True
        yield conn

    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance['database_autodiscovery']['include'].append(database_to_find)
    pg_instance['relations'] = ['pg_index']
    del pg_instance['dbname']
    pg_instance["database_autodiscovery"]['refresh'] = 1
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = NUM_DOGS_DATABASES - len(DISCOVERY_CONFIG["exclude"])
    assert len(databases) == expected_len

    with get_postgres_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_to_find)))

            time.sleep(pg_instance["database_autodiscovery"]['refresh'])
            databases = check.autodiscovery.get_items()
            assert len(databases) == expected_len + 1
        finally:
            # Need to drop the new database to clean up the environment for next tests.
            cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE);").format(sql.Identifier(database_to_find)))


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_relations_disabled(integration_check, pg_instance):
    """
    If no relation metrics are being collected, autodiscovery should not run.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = []
    del pg_instance['dbname']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_collect_all_relations(aggregator, integration_check, pg_instance):
    """
    Check that relation metrics get collected for each database discovered.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance["database_autodiscovery"]["include"] = ["dogs$", "dogs_noschema$", "dogs_nofunc$"]
    pg_instance['relations'] = [
        {'relation_regex': '.*'},
    ]
    del pg_instance['dbname']

    check = integration_check(pg_instance)
    check.check(pg_instance)

    # assert that for all databases found, a relation metric was reported
    databases = check.autodiscovery.get_items()
    for db in databases:
        expected_tags = _get_expected_tags(check, pg_instance, db=db, table='breed', schema='public')
        for metric in RELATION_METRICS:
            aggregator.assert_metric(metric, tags=expected_tags)

    aggregator.assert_metric(
        'dd.postgres._collect_relations_autodiscovery.time',
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_exceeds_min_interval(aggregator, integration_check, pg_instance):
    """
    Check that relation metrics get collected for each database discovered.
    """
    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance["database_autodiscovery"]["include"] = ["dogs$", "dogs_noschema$", "dogs_nofunc$"]
    pg_instance['relations'] = [
        {'relation_regex': '.*'},
    ]
    pg_instance['min_collection_interval'] = 0.001
    del pg_instance['dbname']

    check = integration_check(pg_instance)
    check.check(pg_instance)

    aggregator.assert_metric(
        'dd.postgres._collect_relations_autodiscovery.time',
    )
    assert len(check.warnings) == 1
    test_structure = re.compile(
        "Collecting metrics on autodiscovery metrics took .* ms, which is longer than "
        "the minimum collection interval. Consider increasing the min_collection_interval parameter "
        "in the postgres yaml configuration.\n"
    )
    assert test_structure.match(check.warnings[0])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_dbname_specified(integration_check, pg_instance):
    """
    If a dbname is specified in the config, autodiscovery should not run.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = ['breed']
    pg_instance['dbname'] = "dogs_30"

    with pytest.raises(ConfigurationError):
        integration_check(pg_instance)
