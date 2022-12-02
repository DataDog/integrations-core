import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.postgres.statement_samples import DBExplainError
from datadog_checks.postgres.version_utils import V12

from .common import DB_NAME


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
def test_explain_parameterized_queries(integration_check, dbm_instance, aggregator, query, expected_explain_err_code):
    check = integration_check(dbm_instance)
    check._connect()

    check.check(dbm_instance)
    if check.version < V12:
        return

    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(DB_NAME, query, query, query)
    assert plan_dict is not None
    assert explain_err_code == expected_explain_err_code
    assert err is None

    explain_param_queries = check.statement_samples._explain_parameterized_queries
    # check that we deallocated the prepared statement after explaining
    rows = explain_param_queries._execute_query_and_fetch_rows(
        DB_NAME,
        "SELECT * FROM pg_prepared_statements WHERE name = 'dd_{query_signature}'".format(
            query_signature=compute_sql_signature(query)
        ),
    )
    assert len(rows) == 0


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
def test_explain_parameterized_queries_generic_params(
    integration_check, dbm_instance, aggregator, query, expected_generic_values
):
    check = integration_check(dbm_instance)
    check._connect()

    check.check(dbm_instance)
    if check.version < V12:
        return

    query_signature = compute_sql_signature(query)

    explain_param_queries = check.statement_samples._explain_parameterized_queries
    assert explain_param_queries._create_prepared_statement(DB_NAME, query, query, query_signature) is True
    assert expected_generic_values == explain_param_queries._get_number_of_parameters_for_prepared_statement(
        DB_NAME, query_signature
    )
