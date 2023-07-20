# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from contextlib import nullcontext as does_not_raise

import pytest

from datadog_checks.base.types import ServiceCheck
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS
from tests.common import METRICS


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize(
    'instance, expected_exception, expected_service_checks, expected_events',
    [
        (
            {'api_url': 'http://bad_host:8080/api/v48/', 'tags': ['test1']},
            pytest.raises(
                Exception,
                match='HTTPConnectionPool',
            ),
            [
                {
                    'status': ServiceCheck.CRITICAL,
                    'message': None,
                    'tags': ['api_url:http://bad_host:8080/api/v48/', 'test1'],
                },
            ],
            [],
        ),
        (
            {'api_url': 'http://localhost:8080/api/v48/', 'tags': ['test1']},
            does_not_raise(),
            [
                {
                    'status': ServiceCheck.OK,
                    'message': None,
                    'tags': ['api_url:http://localhost:8080/api/v48/', 'test1'],
                }
            ],
            [
                {
                    'count': 1,
                    'msg_text': "ExecutionException running extraction tasks for service 'cod--qfdcinkqrzw::yarn'.",
                }
            ],
        ),
    ],
    ids=['bad url', 'good url'],
)
def test_api_urls(
    aggregator,
    dd_run_check,
    cloudera_check,
    instance,
    expected_exception,
    expected_service_checks,
    expected_events,
):
    with expected_exception:
        check = cloudera_check(instance)
        dd_run_check(check)
        aggregator.assert_service_check(
            'cloudera.cluster.health',
            ServiceCheck.OK,
            tags=['_cldr_cb_clustertype:Data Hub', '_cldr_cb_origin:cloudbreak', 'cloudera_cluster:cluster_1', 'test1'],
        )
        aggregator.assert_service_check(
            'cloudera.host.health',
            ServiceCheck.OK,
            tags=[
                '_cldr_cm_host_template_name:gateway',
                'cloudera_cluster:cluster_1',
                'cloudera_hostname:cod--qfdcinkqrzw-gateway0.agent-in.jfha-h5rc.a0.cloudera.site',
                'cloudera_rack_id:/ap-northeast-1d',
                'test1',
            ],
        )
        for category, metrics in METRICS.items():
            for metric in metrics:
                aggregator.assert_metric(f'cloudera.{category}.{metric}', at_least=1, tags=[])
                aggregator.assert_metric_has_tag(f'cloudera.{category}.{metric}', "cloudera_cluster:cluster_1")
                aggregator.assert_metric_has_tag(f'cloudera.{category}.{metric}', "test1")
        # All timeseries metrics should have cloudera_{category} tag
        for category, metrics in TIMESERIES_METRICS.items():
            for metric in metrics:
                aggregator.assert_metric_has_tag_prefix(f'cloudera.{category}.{metric}', f"cloudera_{category}")
        aggregator.assert_all_metrics_covered()
        for expected_event in expected_events:
            aggregator.assert_event(expected_event.get('msg_text'), count=expected_event.get('count'))
    for expected_service_check in expected_service_checks:
        aggregator.assert_service_check(
            'cloudera.can_connect',
            status=expected_service_check.get('status'),
            message=expected_service_check.get('message'),
            tags=expected_service_check.get('tags'),
        )


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize(
    'instance',
    [
        {'api_url': 'http://localhost:8080/api/v48/'},
    ],
    ids=['metadata from good url'],
)
def test_metadata(instance, cloudera_check, dd_run_check, datadog_agent):
    check = cloudera_check(instance)
    check.check_id = 'test:123'
    dd_run_check(check)
    raw_version = '7.2.15'
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'cloudera',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
@pytest.mark.parametrize(
    'instance, expected_service_checks, expected_metrics, expected_caplog_text',
    [
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'custom_queries': [
                    {
                        'query': "SELECT jvm_gc_rate, jvm_free_memory",
                        'tags': ["custom_tag:1"],
                    },
                ],
            },
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [
                {
                    'count': 1,
                    'name': 'cloudera.cmserver.jvm_gc_rate',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
                {
                    'count': 1,
                    'name': 'cloudera.cmserver.jvm_free_memory',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
            ],
            None,
        ),
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'custom_queries': [
                    {
                        'query': "SELECT jvm_gc_rate as foo",
                        'tags': ["custom_tag:1"],
                    },
                ],
            },
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [
                {
                    'count': 1,
                    'name': 'cloudera.cmserver.foo',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
                {
                    'count': 0,
                    'name': 'cloudera.cmserver.jvm_gc_rate',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
            ],
            None,
        ),
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'custom_queries': [
                    {
                        'query': "SELECT last(jvm_gc_rate) as jvm_gc_rate, last(jvm_free_memory) as jvm_free_memory",
                        'tags': ["custom_tag:1"],
                    },
                ],
            },
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [
                {
                    'count': 1,
                    'name': 'cloudera.cmserver.jvm_gc_rate',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
                {
                    'count': 1,
                    'name': 'cloudera.cmserver.jvm_free_memory',
                    'tags': ['custom_tag:1', 'cloudera_cmserver:cloudera_manager_server'],
                },
            ],
            None,
        ),
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'custom_queries': [
                    {
                        'query': "select fake_foo",  # fake_foo doesn't exist
                        'tags': ["baz"],
                    }
                ],
            },
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [
                {
                    'count': 0,
                    'name': 'cloudera.fake_foo',
                    'tags': ['baz'],
                },
            ],
            "Invalid metric 'fake_foo' in 'select fake_foo'",
        ),
        (
            {
                'api_url': 'http://localhost:8080/api/v48/',
                'custom_queries': [
                    {
                        'query': "selectt",
                        'tags': ["baz"],
                    }
                ],
            },
            [
                {
                    'status': ServiceCheck.OK,
                    'tags': ['api_url:http://localhost:8080/api/v48/'],
                }
            ],
            [],
            "Invalid syntax: no viable alternative at input 'selectt'.",
        ),
    ],
    ids=[
        'metrics no alias',
        'metrics with alias',
        'metrics last alias',
        'non existent metric custom query',
        'incorrect formatting custom query',
    ],
)
def test_custom_queries(
    instance,
    expected_service_checks,
    expected_metrics,
    expected_caplog_text,
    aggregator,
    dd_run_check,
    cloudera_check,
    caplog,
):
    caplog.clear()
    caplog.set_level(logging.WARNING)
    check = cloudera_check(instance)
    dd_run_check(check)
    for expected_service_check in expected_service_checks:
        aggregator.assert_service_check(
            'cloudera.can_connect',
            status=expected_service_check.get('status'),
            message=expected_service_check.get('message'),
            tags=expected_service_check.get('tags'),
        )
    for expected_metric in expected_metrics:
        aggregator.assert_metric(expected_metric['name'], tags=expected_metric['tags'], count=expected_metric['count'])
    if expected_caplog_text:
        assert expected_caplog_text in caplog.text
