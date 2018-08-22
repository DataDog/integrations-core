# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import logging
import copy

from . import common

log = logging.getLogger(__file__)

CHECK_GAUGES = [
    '{}.memstats.alloc',
    '{}.memstats.heap_alloc',
    '{}.memstats.heap_idle',
    '{}.memstats.heap_inuse',
    '{}.memstats.heap_objects',
    '{}.memstats.heap_released',
    '{}.memstats.heap_sys',
    '{}.memstats.total_alloc',
]

# this is a histogram
CHECK_GAUGES_DEFAULT = [
    '{}.memstats.pause_ns',
]

CHECK_RATES = [
    '{}.memstats.frees',
    '{}.memstats.lookups',
    '{}.memstats.mallocs',
    '{}.memstats.num_gc',
    '{}.memstats.pause_total_ns',
]

CHECK_GAUGES_CUSTOM_MOCK = {
    '{}.gauge1': ['metric_tag1:metric_value1',
                  'metric_tag2:metric_value2',
                  'path:random_walk'],
    '{}.memstats.by_size.1.mallocs': []
}

CHECK_RATES_CUSTOM_MOCK = ['{}.gc.pause']


MOCK_CONFIG = {
    "expvar_url": common.URL_WITH_PATH,
    "tags": ["optionaltag1", "optionaltag2"],
    "metrics": [
        {
            # Contains list traversal and default values
            "path": "memstats/BySize/1/Mallocs",
        },
        {
            "path": "memstats/PauseTotalNs",
            "alias": "go_expvar.gc.pause",
            "type": "rate"
        },
        {
            "path": "random_walk",
            "alias": "go_expvar.gauge1",
            "type": "gauge",
            "tags": ["metric_tag1:metric_value1", "metric_tag2:metric_value2"]
        }
    ]
}

CONFIG = {
    "expvar_url": common.URL_WITH_PATH,
    'tags': ['my_tag'],
    'metrics': [
        {
            'path': 'num_calls',
            "type": "rate"
        },
    ]
}


@pytest.mark.unit
def test_go_expvar_mocked(go_expvar_mock, check, aggregator):
    check.check(MOCK_CONFIG)

    shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(common.URL_WITH_PATH)]

    for gauge in CHECK_GAUGES_DEFAULT:
        aggregator.assert_metric(gauge.format(common.CHECK_NAME),
                                 count=2, tags=shared_tags)

    for gauge in CHECK_GAUGES:
        aggregator.assert_metric(gauge.format(common.CHECK_NAME),
                                 count=1, tags=shared_tags)
    for gauge, tags in CHECK_GAUGES_CUSTOM_MOCK.iteritems():
        aggregator.assert_metric(gauge.format(common.CHECK_NAME),
                                 count=1, tags=shared_tags + tags)

    for rate in CHECK_RATES:
        aggregator.assert_metric(rate.format(common.CHECK_NAME),
                                 count=1, tags=shared_tags)
    for rate in CHECK_RATES_CUSTOM_MOCK:
        aggregator.assert_metric(rate.format(common.CHECK_NAME),
                                 count=1, tags=shared_tags + ['path:memstats.PauseTotalNs'])

    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_go_expvar_mocked_namespace(go_expvar_mock, check, aggregator):
    metric_namespace = "testingapp"

    # adjust mock config to set a namespace value
    mock_config = {
        "namespace": metric_namespace,
        "expvar_url": common.URL_WITH_PATH,
        "tags": ["optionaltag1", "optionaltag2"],
        "metrics": [
            {
                # Contains list traversal and default values
                "path": "memstats/BySize/1/Mallocs",
            },
            {
                "path": "memstats/PauseTotalNs",
                "alias": "{0}.gc.pause".format(metric_namespace),
                "type": "rate"
            },
            {
                "path": "random_walk",
                "alias": "{0}.gauge1".format(metric_namespace),
                "type": "gauge",
                "tags": ["metric_tag1:metric_value1", "metric_tag2:metric_value2"]
            }
        ]
    }

    check.check(mock_config)

    shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(common.URL_WITH_PATH)]

    for gauge in CHECK_GAUGES_DEFAULT:
        aggregator.assert_metric(gauge.format(metric_namespace),
                                 count=2, tags=shared_tags)

    for gauge in CHECK_GAUGES:
        aggregator.assert_metric(gauge.format(metric_namespace),
                                 count=1, tags=shared_tags)
    for gauge, tags in CHECK_GAUGES_CUSTOM_MOCK.iteritems():
        aggregator.assert_metric(gauge.format(metric_namespace),
                                 count=1, tags=shared_tags + tags)

    for rate in CHECK_RATES:
        aggregator.assert_metric(rate.format(metric_namespace),
                                 count=1, tags=shared_tags)
    for rate in CHECK_RATES_CUSTOM_MOCK:
        aggregator.assert_metric(rate.format(metric_namespace),
                                 count=1, tags=shared_tags + ['path:memstats.PauseTotalNs'])

    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_max_metrics(go_expvar_mock, check, aggregator):
    config_max = copy.deepcopy(MOCK_CONFIG)
    config_max['max_returned_metrics'] = 1

    check.check(config_max)

    shared_tags = ['optionaltag1', 'optionaltag2', 'expvar_url:{0}'.format(common.URL_WITH_PATH)]

    # Default metrics
    for gauge in CHECK_GAUGES_DEFAULT:
        aggregator.assert_metric(gauge.format(common.CHECK_NAME),
                                 count=2, tags=shared_tags)

    # And then check limitation, will fail at the coverage_report if incorrect
    aggregator.assert_metric('go_expvar.memstats.alloc', count=1, tags=shared_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_deep_get(go_expvar_mock, check, aggregator):
    # Wildcard for dictkeys
    content = {
        'a': {
            'one': 1,
            'two': 2
        },
        'b': {
            'three': 3,
            'four':  4
        }
    }
    expected = [
        (['a', 'two'], 2),
        (['b', 'three'], 3),
    ]
    check.check(MOCK_CONFIG)

    results = check.deep_get(content, ['.', 't.*'], [])
    assert sorted(results) == sorted(expected)

    expected = [(['a', 'one'], 1)]
    results = check.deep_get(content, ['.', 'one'], [])
    assert sorted(results) == sorted(expected)

    # Wildcard for list index
    content = {
        'list': [
            {
                'timestamp': 10,
                'value':     5
            },
            {
                'timestamp': 10,
                'value':     10
            },
            {
                'timestamp': 10,
                'value':     20
            }
        ]
    }
    expected = [
        (['list', '0', 'value'], 5),
        (['list', '1', 'value'], 10),
        (['list', '2', 'value'], 20)
    ]

    results = check.deep_get(content, ['list', '.*', 'value'], [])
    assert sorted(results) == sorted(expected)


# Test that the path tags get correctly added when metric has alias
@pytest.mark.unit
def test_alias_tag_path(go_expvar_mock, check, aggregator):
    mock_config = {
        "expvar_url": common.URL_WITH_PATH,
        "metrics": [
            {
                "path": "array/\d+/key",
                "alias": "array.dict.key",
                "type": "gauge",
            }
        ]
    }
    check.check(mock_config)

    shared_tags = ['expvar_url:{0}'.format(common.URL_WITH_PATH)]
    aggregator.assert_metric("array.dict.key", count=1, tags=shared_tags + ["path:array.0.key"])
    aggregator.assert_metric("array.dict.key", count=1, tags=shared_tags + ["path:array.1.key"])
