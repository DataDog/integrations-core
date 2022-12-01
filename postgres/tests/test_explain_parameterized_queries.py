import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.postgres.explain_parameterized_queries import ExplainParameterizedQueries
from datadog_checks.postgres.statement_samples import DBExplainError

from .common import DB_NAME, PORT


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
    "query,expected_explain_err_code,expected_generic_values",
    [
        ("SELECT * FROM pg_settings WHERE name = $1", DBExplainError.explained_with_prepared_statement, 1),
        (
            "SELECT * FROM pg_settings WHERE name = $1 AND "
            "context = (SELECT context FROM pg_settings WHERE vartype = $2) AND source = $3",
            DBExplainError.explained_with_prepared_statement,
            3,
        ),
    ],
)
def test_explain_parameterized_queries(
    integration_check, dbm_instance, aggregator, query, expected_explain_err_code, expected_generic_values
):
    check = integration_check(dbm_instance)
    check._connect()

    check.check(dbm_instance)
    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
        "datadog_test", query, query, query
    )
    assert plan_dict is not None
    assert explain_err_code == expected_explain_err_code
    assert err is None

    explain_param_queries = check.statement_samples._explain_parameterized_queries
    assert expected_generic_values == explain_param_queries._get_number_of_parameters_for_prepared_statement(
        DB_NAME, compute_sql_signature(query)
    )

    expected_tags = dbm_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
    ]
    # the value of this metric varies, to prevent a flaky test, just assert that this metric is emitted
    aggregator.assert_metric(
        'dd.postgres.explain_parameterized_queries.size',
        tags=expected_tags,
        hostname='stubbed.hostname',
    )

    expected_pg_prepared_statements_max_space = check._config.statement_samples_config.get(
        'max_pg_prepared_statements_space', ExplainParameterizedQueries.DEFAULT_MAX_ALLOWABLE_SPACE_MB
    )
    aggregator.assert_metric(
        'dd.postgres.explain_parameterized_queries.max',
        tags=expected_tags,
        value=expected_pg_prepared_statements_max_space,
        hostname='stubbed.hostname',
    )


def test_explain_parameterized_queries_max_space(integration_check, dbm_instance, aggregator):
    check = integration_check(dbm_instance)
    check._connect()

    check.check(dbm_instance)
    query = "SELECT * FROM pg_settings WHERE name = $1"

    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
        "datadog_test", query, query, query
    )
    assert plan_dict is not None
    assert explain_err_code == DBExplainError.explained_with_prepared_statement
    assert err is None

    explain_param_queries = check.statement_samples._explain_parameterized_queries

    rows_before_reset = explain_param_queries._execute_query_and_fetch_rows(
        DB_NAME, "SELECT * FROM pg_prepared_statements"
    )
    assert len(rows_before_reset) > 0

    # we should expect this check run to clear `pg_prepared_statements`
    dbm_instance['query_samples']['max_pg_prepared_statements_space'] = 0
    check.check(dbm_instance)
    plan_dict, explain_err_code, err = check.statement_samples._run_and_track_explain(
        "datadog_test", query, query, query
    )
    assert plan_dict is not None
    assert explain_err_code == DBExplainError.explained_with_prepared_statement
    assert err is None

    rows_after_reset = explain_param_queries._execute_query_and_fetch_rows(
        DB_NAME, "SELECT * FROM pg_prepared_statements"
    )
    assert len(rows_after_reset) == 0

    expected_tags = dbm_instance['tags'] + [
        'db:{}'.format(DB_NAME),
        'port:{}'.format(PORT),
    ]
    aggregator.assert_metric(
        'dd.postgres.explain_parameterized_queries.size',
        tags=expected_tags,
        value=0,
        hostname='stubbed.hostname',
    )
    aggregator.assert_metric(
        'dd.postgres.explain_parameterized_queries.max',
        tags=expected_tags,
        value=0,
        hostname='stubbed.hostname',
    )
