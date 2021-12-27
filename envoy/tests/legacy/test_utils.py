from datadog_checks.envoy.utils import make_metric_tree

from .common import requires_legacy_environment

pytestmark = [requires_legacy_environment]


def test_make_metric_tree():
    # fmt: off
    metrics = {
        'http.dynamodb.error': {
            'tags': (
                ('stat_prefix', ),
                (),
                ('table_name', 'error_type', ),
            ),
            'method': 'count',
        },
        'http.dynamodb.error.BatchFailureUnprocessedKeys': {
            'tags': (
                ('stat_prefix', ),
                (),
                ('table_name', ),
                (),
            ),
            'method': 'count',
        },
    }

    assert make_metric_tree(metrics) == {
        'http': {
            'dynamodb': {
                'error': {
                    'BatchFailureUnprocessedKeys': {
                        '|_tags_|': [
                            (),
                        ],
                    },
                    '|_tags_|': [
                        ('table_name', 'error_type', ),
                        ('table_name', ),
                    ],
                },
                '|_tags_|': [
                    (),
                ],
            },
            '|_tags_|': [
                ('stat_prefix', ),
            ],
        },
    }
    # fmt: on
