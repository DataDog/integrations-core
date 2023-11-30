# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.envoy.utils import make_metric_tree, modify_metrics_dict

pytestmark = [pytest.mark.unit]


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


def test_wildcard_removal_tree():
    # fmt: off
    metrics = {
        "*.http_local_rate_limit.enabled": {
            "tags": (
                ("stat_prefix",),
                (),
                ()
            ),
            "method": "monotonic_count",
        },
        "*.http_local_rate_limit.enforced": {
            "tags": (
                ("stat_prefix",),
                (),
                ()
            ),
            "method": "monotonic_count",
        }
    }

    assert modify_metrics_dict(metrics) == {
        "http_local_rate_limit.enabled": {
            "tags": (("stat_prefix",), (), ()),
            "method": "monotonic_count",
        },
        "http_local_rate_limit.enforced": {
            "tags": (("stat_prefix",), (), ()),
            "method": "monotonic_count",
        }
    }
    # fmt: on
