# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from .common import _get_expected_tags


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, pg_instance, dd_run_check, integration_check):
    pg_instance.update(
        {
            'custom_queries': [
                {
                    'metric_prefix': 'custom',
                    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                    'tags': ['query:custom'],
                },
                {
                    'metric_prefix': 'another_custom_one',
                    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                    'tags': ['query:another_custom_one'],
                },
            ]
        }
    )
    postgres_check = integration_check(pg_instance)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('another_custom_one.num', value=value, tags=custom_tags + ['query:another_custom_one'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'query, expected_value',
    [
        pytest.param("SET LOCAL statement_timeout = '15s'; SELECT 1", 1, id='set-local-before-select'),
        pytest.param(
            "CREATE TEMP TABLE multi_statement (v int) ON COMMIT DROP; "
            "INSERT INTO multi_statement VALUES (2); "
            "SELECT v FROM multi_statement",
            2,
            id='ddl-and-dml-before-select',
        ),
        pytest.param("SELECT 3 WHERE false; SELECT 4", None, id='empty-select-is-not-skipped'),
    ],
)
def test_multi_statement_custom_query(aggregator, pg_instance, dd_run_check, integration_check, query, expected_value):
    # Regression test for https://github.com/DataDog/integrations-core/issues/25954: the metric comes from the first
    # statement that returns a result set, even when earlier statements return none.
    pg_instance.update(
        {
            'custom_queries': [
                {
                    'metric_prefix': 'custom',
                    'query': query,
                    'columns': [{'name': 'value', 'type': 'gauge'}],
                },
            ]
        }
    )
    postgres_check = integration_check(pg_instance)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    if expected_value is None:
        aggregator.assert_metric('custom.value', count=0)
    else:
        aggregator.assert_metric('custom.value', value=expected_value, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_both_global_and_instance_custom_queries(aggregator, pg_instance, dd_run_check, integration_check):
    pg_instance.update(
        {
            'custom_queries': [
                {
                    'metric_prefix': 'custom',
                    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                    'tags': ['query:custom'],
                },
            ],
            'use_global_custom_queries': 'extend',
        }
    )
    pg_init_config = {
        'global_custom_queries': [
            {
                'metric_prefix': 'global_custom',
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                'tags': ['query:global_custom'],
            },
        ]
    }
    postgres_check = integration_check(pg_instance, pg_init_config)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_only_global_custom_queries(aggregator, pg_instance, dd_run_check, integration_check):
    pg_init_config = {
        'global_custom_queries': [
            {
                'metric_prefix': 'global_custom',
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                'tags': ['query:global_custom'],
            },
        ]
    }
    postgres_check = integration_check(pg_instance, pg_init_config)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_only_instance_custom_queries(aggregator, pg_instance, dd_run_check, integration_check):
    pg_instance.update(
        {
            'custom_queries': [
                {
                    'metric_prefix': 'custom',
                    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                    'tags': ['query:custom'],
                },
            ],
            'use_global_custom_queries': 'false',
        }
    )
    pg_init_config = {
        'global_custom_queries': [
            {
                'metric_prefix': 'global_custom',
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                'tags': ['query:global_custom'],
            },
        ]
    }
    postgres_check = integration_check(pg_instance, pg_init_config)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'], count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_only_custom_queries(aggregator, pg_instance, dd_run_check, integration_check):
    pg_instance.update(
        {
            'only_custom_queries': True,
            'custom_queries': [
                {
                    'metric_prefix': 'custom',
                    'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                    'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
                    'tags': ['query:custom'],
                },
            ],
        }
    )
    postgres_check = integration_check(pg_instance)
    dd_run_check(postgres_check)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])

    running_tags = _get_expected_tags(postgres_check, pg_instance)
    aggregator.assert_metric('postgresql.running', count=1, value=1, tags=running_tags)
    aggregator.assert_all_metrics_covered()
