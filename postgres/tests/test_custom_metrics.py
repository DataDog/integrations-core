# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres import PostgreSql

from .common import _get_expected_tags


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_metrics(aggregator, pg_instance):
    pg_instance.update(
        {
            'relations': ['persons'],
            'custom_metrics': [
                {
                    'descriptors': [('letter', 'customdb')],
                    'metrics': {'num': ['custom.num', 'Gauge']},
                    'query': (
                        "SELECT letter, %s FROM (VALUES (21, 'a'), (22, 'b'), (23, 'c')) AS t (num,letter) LIMIT 1"
                    ),
                    'relation': False,
                }
            ],
        }
    )
    postgres_check = PostgreSql('postgres', {}, [pg_instance])
    postgres_check.check(pg_instance)

    tags = _get_expected_tags(postgres_check, pg_instance, customdb='a')
    aggregator.assert_metric('custom.num', value=21, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, pg_instance):
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
    postgres_check = PostgreSql('postgres', {}, [pg_instance])
    postgres_check.check(pg_instance)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('another_custom_one.num', value=value, tags=custom_tags + ['query:another_custom_one'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_both_global_and_instance_custom_queries(aggregator, pg_instance):
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
    postgres_check = PostgreSql('postgres', pg_init_config, [pg_instance])
    postgres_check.check(pg_instance)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_only_global_custom_queries(aggregator, pg_instance):
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
            'use_global_custom_queries': 'true',
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
    postgres_check = PostgreSql('postgres', pg_init_config, [pg_instance])
    postgres_check.check(pg_instance)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'], count=0)
        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_only_instance_custom_queries(aggregator, pg_instance):
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
    postgres_check = PostgreSql('postgres', pg_init_config, [pg_instance])
    postgres_check.check(pg_instance)
    tags = _get_expected_tags(postgres_check, pg_instance, with_db=True)

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = [f'customtag:{tag}']
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags + ['query:custom'])
        aggregator.assert_metric('global_custom.num', value=value, tags=custom_tags + ['query:global_custom'], count=0)
