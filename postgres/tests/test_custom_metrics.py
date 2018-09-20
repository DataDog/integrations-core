# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.postgres import PostgreSql


@pytest.mark.integration
def test_custom_metrics(aggregator, postgres_standalone, pg_instance):
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

    aggregator.assert_metric('custom.num', value=21, tags=['customdb:a'] + pg_instance['tags'])


@pytest.mark.integration
def test_custom_queries(aggregator, postgres_standalone, pg_instance):
    pg_instance.update({
        'custom_queries': [{
            'metric_prefix': 'custom',
            'query': "SELECT letter, num FROM (VALUES (21, 'a'), (22, 'b'), (23, 'c')) AS t (num,letter) LIMIT 1",
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
        }],
    })
    postgres_check = PostgreSql('postgres', {}, {})
    postgres_check.check(pg_instance)
    tags = ['customtag:a', 'db:{}'.format(pg_instance['dbname'])] + pg_instance['tags']
    aggregator.assert_metric('custom.num', value=21, tags=tags)
