# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from contextlib import contextmanager
import copy
import select
import time

from .utils import run_one_check
from .test_relations import RELATION_METRICS
from .common import HOST, USER_ADMIN, PASSWORD_ADMIN, _get_expected_tags
from datadog_checks.postgres import PostgreSql
from datadog_checks.postgres.connections import MultiDatabaseConnectionPool


import psycopg2
import psycopg2.sql
import pytest

DISCOVERY_CONFIG = {
    "enabled": True,
    "include": ["dogs_([1-9]|[1-9][0-9]|10[0-9])"],
    "exclude":["dogs_5$", "dogs_50$"],
}

@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_simple(integration_check, pg_instance):
    """
    Test simple autodiscovery.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = ['pg_index']
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = (100-len(DISCOVERY_CONFIG["exclude"]))
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
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    assert len(databases) == pg_instance['database_autodiscovery']['max_databases']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_refresh(integration_check, pg_instance):
    """
    Test cache refresh by adding a database in the middle of a check.
    """
    database_to_find = "cats"
    @contextmanager
    def get_postgres_connection():
        conn_args = {'host': HOST, 'dbname': "postgres", 'user': USER_ADMIN, 'password': PASSWORD_ADMIN}
        conn = psycopg2.connect(**conn_args)
        conn.autocommit = True
        yield conn

    pg_instance["database_autodiscovery"] = copy.deepcopy(DISCOVERY_CONFIG)
    pg_instance['database_autodiscovery']['include'].append(database_to_find)
    pg_instance['relations'] = ['pg_index']
    pg_instance["database_autodiscovery"]['refresh'] = 1
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is not None
    databases = check.autodiscovery.get_items()
    expected_len = (100-len(DISCOVERY_CONFIG["exclude"]))
    assert len(databases) == expected_len

    with get_postgres_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(psycopg2.sql.SQL("CREATE DATABASE {}").format(psycopg2.sql.Identifier(database_to_find)))

        time.sleep(pg_instance["database_autodiscovery"]['refresh'])
        databases = check.autodiscovery.get_items()
        assert len(databases) == expected_len+1
        # Need to drop the new database to clean up the environment for next tests.
        cursor.execute(psycopg2.sql.SQL("DROP DATABASE {} WITH (FORCE);").format(psycopg2.sql.Identifier(database_to_find)))


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_relations_disabled(integration_check, pg_instance):
    """
    If no relation metrics are being collected, autodiscovery should not run.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = []
    check = integration_check(pg_instance)
    run_one_check(check, pg_instance)

    assert check.autodiscovery is None


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_autodiscovery_collect_all_relations(aggregator, integration_check, pg_instance):
    """
    If no relation metrics are being collected, autodiscovery should not run.
    """
    pg_instance["database_autodiscovery"] = DISCOVERY_CONFIG
    pg_instance['relations'] = ["breed"]
    del pg_instance['dbname']

    check = integration_check(pg_instance)
    check.check(pg_instance)

    # assert that for all databases found, a relation metric was reported
    databases = check.autodiscovery.get_items()
    for db in databases:
        print(RELATION_METRICS)
        expected_tags = _get_expected_tags(check, pg_instance, db=db, table='breed', schema='public')
        for metric in RELATION_METRICS:
            aggregator.assert_metric(metric, tags=expected_tags)
            print("yay {}".format(metric))
    
    assert None is not None