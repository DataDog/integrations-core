from datadog_checks.envoy.utils import make_metric_tree


def test_make_metric_tree():
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

    exp = {
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

    mt = make_metric_tree(metrics)
    print(mt)
    print(exp)
    assert mt==exp
