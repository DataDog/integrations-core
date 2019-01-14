# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.postgres import PostgreSql


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_metrics(aggregator, pg_instance):
    pg_instance.update({
        'relations': ['persons'],
        'custom_metrics': [{
            'descriptors': [('letter', 'customdb')],
            'metrics': {
                'num': ['custom.num', 'Gauge']
            },
            'query': "SELECT letter, %s FROM (VALUES (21, 'a'), (22, 'b'), (23, 'c')) AS t (num,letter) LIMIT 1",
            'relation': False,
        }],
    })
    postgres_check = PostgreSql('postgres', {}, {})
    postgres_check.check(pg_instance)

    tags = pg_instance['tags'] + [
        'pg_instance:{}-{}'.format(pg_instance['host'], pg_instance['port']),
        'customdb:a',
    ]
    aggregator.assert_metric('custom.num', value=21, tags=tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_custom_queries(aggregator, pg_instance):
    pg_instance.update({
        'custom_queries': [
            {
                'metric_prefix': 'custom',
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                'columns': [
                    {
                        'name': 'customtag',
                        'type': 'tag',
                    },
                    {
                        'name': 'num',
                        'type': 'gauge',
                    }
                ],
            },
            {
                'metric_prefix': 'another_custom_one',
                'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
                'columns': [
                    {
                        'name': 'customtag',
                        'type': 'tag',
                    },
                    {
                        'name': 'num',
                        'type': 'gauge',
                    }
                ],
            }
        ],
    })
    postgres_check = PostgreSql('postgres', {}, {})
    postgres_check.check(pg_instance)
    tags = ['db:{}'.format(pg_instance['dbname'])]
    tags.extend(pg_instance['tags'])

    for tag in ('a', 'b', 'c'):
        value = ord(tag)
        custom_tags = ['customtag:{}'.format(tag)]
        custom_tags.extend(tags)

        aggregator.assert_metric('custom.num', value=value, tags=custom_tags)
        aggregator.assert_metric('another_custom_one.num', value=value, tags=custom_tags)
