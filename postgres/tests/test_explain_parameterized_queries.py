# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest import mock

import psycopg
import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.postgres.util import DBExplainError
from datadog_checks.postgres.version_utils import V12

from .common import DB_NAME
from .utils import requires_over_12


@pytest.fixture
def dbm_instance(pg_instance):
    pg_instance['dbm'] = True
    pg_instance['min_collection_interval'] = 1
    pg_instance['pg_stat_activity_view'] = "datadog.pg_stat_activity()"
    pg_instance['query_samples'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 1,
        'explain_parameterized_queries': True,
    }
    pg_instance['query_activity'] = {'enabled': True, 'collection_interval': 1}
    pg_instance['query_metrics'] = {'enabled': True, 'run_sync': True, 'collection_interval': 10}
    return pg_instance


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
@requires_over_12
@pytest.mark.parametrize(
    "query,expected_explain_err_code",
    [
        ("SELECT * FROM pg_settings WHERE name = $1", DBExplainError.explained_with_prepared_statement),
        (
            "SELECT * FROM pg_settings WHERE name = $1 AND "
            "context = (SELECT context FROM pg_settings WHERE vartype = $2) AND source = $3",
            DBExplainError.explained_with_prepared_statement,
        ),
    ],
)
def test_explain_parameterized_queries(integration_check, dbm_instance, query, expected_explain_err_code):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)

    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
        DB_NAME, query, query, "7231596c8b5536d1"
    )
    assert plan_dict is not None
    assert explain_err_code == expected_explain_err_code
    assert err is None

    explain_param_queries = check.statement_samples._explain_parameterized_queries
    # check that we deallocated the prepared statement after explaining
    with check.db_pool.get_connection(DB_NAME) as conn:
        rows = explain_param_queries._execute_query_and_fetch_rows(
            conn,
            "SELECT * FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'".format(
                query_signature=compute_sql_signature(query)
            ),
        )
    assert len(rows) == 0


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
@requires_over_12
@pytest.mark.parametrize(
    "query,expected_generic_values",
    [
        ("SELECT * FROM pg_settings WHERE name = $1", 1),
        (
            "SELECT * FROM pg_settings WHERE name = $1 AND "
            "context = (SELECT context FROM pg_settings WHERE vartype = $2) AND source = $3",
            3,
        ),
    ],
)
def test_explain_parameterized_queries_generic_params(integration_check, dbm_instance, query, expected_generic_values):
    check = integration_check(dbm_instance)

    query_signature = compute_sql_signature(query)

    explain_param_queries = check.statement_samples._explain_parameterized_queries
    with check.db_pool.get_connection(DB_NAME) as conn:
        explain_param_queries._create_prepared_statement(conn, query, query, query_signature)
        assert expected_generic_values == explain_param_queries._get_number_of_parameters_for_prepared_statement(
            conn, query_signature
        )


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_explain_parameterized_queries_version_below_12(integration_check, dbm_instance):
    '''
    For postgres versions below 12, we do not support explaining parameterized queries,
    because plan_cache_mode is not supported. We should return proper error.
    '''
    check = integration_check(dbm_instance)
    check.check(dbm_instance)
    if check.version >= V12:
        # this test is for versions below 12 to make sure we return proper error for unsupported versions
        return

    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
        DB_NAME,
        "SELECT * FROM pg_settings WHERE name = $1",
        "SELECT * FROM pg_settings WHERE name = $1",
        "7231596c8b5536d1",
    )
    assert plan_dict is None
    assert explain_err_code == DBExplainError.parameterized_query
    assert err is not None
    assert err == "<class 'psycopg.errors.UndefinedParameter'>"


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
@requires_over_12
def test_explain_parameterized_queries_create_prepared_statement_exception(integration_check, dbm_instance):
    check = integration_check(dbm_instance)
    check.check(dbm_instance)

    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._create_prepared_statement',
        side_effect=psycopg.errors.DatabaseError("unexpected exception"),
    ):
        plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
            DB_NAME,
            "SELECT * FROM pg_settings WHERE name = $1",
            "SELECT * FROM pg_settings WHERE name = $1",
            "7231596c8b5536d1",
        )
        assert plan_dict is None
        assert explain_err_code == DBExplainError.failed_to_explain_with_prepared_statement
        assert err is not None
        assert err == "<class 'psycopg.DatabaseError'>"


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
@requires_over_12
def test_explain_parameterized_queries_explain_prepared_statement_exception(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    check.check(dbm_instance)

    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._explain_prepared_statement',
        side_effect=psycopg.errors.DatabaseError("unexpected exception"),
    ):
        query = "SELECT * FROM pg_settings WHERE name = $1"
        plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
            DB_NAME, query, query, "7231596c8b5536d1"
        )
        assert plan_dict is None
        assert explain_err_code == DBExplainError.failed_to_explain_with_prepared_statement
        assert err is not None
        assert err == "<class 'psycopg.DatabaseError'>"
        with check.db_pool.get_connection(DB_NAME) as conn:
            # check that we deallocated the prepared statement after explaining
            rows = check.statement_samples._explain_parameterized_queries._execute_query_and_fetch_rows(
                conn,
                "SELECT * FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'".format(
                    query_signature=compute_sql_signature(query)
                ),
            )
        assert len(rows) == 0


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
@requires_over_12
def test_explain_parameterized_queries_explain_prepared_statement_no_plan_returned(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    check.check(dbm_instance)

    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._execute_query_and_fetch_rows',
        return_value=None,
    ):
        plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
            DB_NAME,
            "SELECT * FROM pg_settings WHERE name = $1",
            "SELECT * FROM pg_settings WHERE name = $1",
            "7231596c8b5536d1",
        )
        assert plan_dict is None
        assert explain_err_code == DBExplainError.no_plan_returned_with_prepared_statement
        assert err is None


@requires_over_12
def test_generate_prepared_statement_query_no_parameters(integration_check, dbm_instance):
    check = integration_check(dbm_instance)
    test_query_signature = "12345678"

    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._get_number_of_parameters_for_prepared_statement',
        return_value=0,
    ):
        prepared_statement_query = (
            check.statement_samples._explain_parameterized_queries._generate_prepared_statement_query(
                None, test_query_signature
            )
        )
        assert prepared_statement_query == f"EXECUTE dd_{test_query_signature}"


def test_generate_prepared_statement_query_three_parameters(integration_check, dbm_instance):
    check = integration_check(dbm_instance)
    test_query_signature = "12345678"

    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._get_number_of_parameters_for_prepared_statement',
        return_value=3,
    ):
        prepared_statement_query = (
            check.statement_samples._explain_parameterized_queries._generate_prepared_statement_query(
                None, test_query_signature
            )
        )
        assert prepared_statement_query == f"EXECUTE dd_{test_query_signature}(null,null,null)"


@pytest.mark.unit
@requires_over_12
def test_create_prepared_statement_exception(integration_check, dbm_instance):
    check = integration_check(dbm_instance)

    query = "SELECT * FROM pg_settings WHERE name = $1"
    query_signature = compute_sql_signature(query)
    with mock.patch(
        'datadog_checks.postgres.explain_parameterized_queries.ExplainParameterizedQueries._execute_query',
        side_effect=Exception,
    ):
        with pytest.raises(Exception):
            check.statement_samples._explain_parameterized_queries._create_prepared_statement(
                DB_NAME, query, query, query_signature
            )


@pytest.mark.unit
@pytest.mark.parametrize(
    "query,statement_is_parameterized_query",
    [
        ("SELECT * FROM products WHERE id = $1", True),
        ("SELECT * FROM products WHERE id = '$1'", False),
        ("SELECT * FROM products WHERE id = $1 AND name = $2", True),
        ("SELECT * FROM products WHERE id = $1 AND name = '$2'", True),
        ("SELECT * FROM products WHERE id = $1 AND name = $2 AND price = 3", True),
        ("SELECT * FROM products WHERE id = $1 AND name = $2 AND price = '3'", True),
        ("SELECT * FROM products WHERE id = $1 AND name = $2 AND price = '$3'", True),
    ],
)
def test_explain_parameterized_queries_is_parameterized_query(
    integration_check, dbm_instance, query, statement_is_parameterized_query
):
    check = integration_check(dbm_instance)
    explain_param_queries = check.statement_samples._explain_parameterized_queries
    assert statement_is_parameterized_query == explain_param_queries._is_parameterized_query(query)
