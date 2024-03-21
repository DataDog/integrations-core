# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy import Envoy
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

from .common import (
    CONNECTION_LIMIT_METRICS,
    CONNECTION_LIMIT_STAT_PREFIX_TAG,
    ENVOY_VERSION,
    EXT_METRICS,
    FLAVOR,
    HOST,
    INSTANCES,
    LOCAL_RATE_LIMIT_METRICS,
    RATE_LIMIT_STAT_PREFIX_TAG,
    RBAC_METRICS,
)

CHECK_NAME = 'envoy'

pytestmark = [pytest.mark.unit]


def test_success_fixture(aggregator, fixture_path, mock_http_response, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)

    response = mock_http_response(file_path=fixture_path('./legacy/multiple_services')).return_value
    dd_run_check(c)

    metrics_collected = 0
    for metric in METRICS:
        metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

    num_metrics = len(response.content.decode().splitlines())
    num_metrics -= sum(c.unknown_metrics.values()) + sum(c.unknown_tags.values())
    assert 4481 <= metrics_collected == num_metrics


def test_retrocompatible_config(check):
    instance = deepcopy(INSTANCES['main'])
    instance['metric_whitelist'] = deepcopy(INSTANCES['included_excluded_metrics']['included_metrics'])
    instance['metric_blacklist'] = deepcopy(INSTANCES['included_excluded_metrics']['excluded_metrics'])

    c1 = check(instance)
    c2 = check(INSTANCES['included_excluded_metrics'])
    assert c1.config_included_metrics == c2.config_included_metrics
    assert c1.config_excluded_metrics == c2.config_excluded_metrics


def test_retrocompatible_config2(check):
    instance = deepcopy(INSTANCES['main'])
    instance['metric_whitelist'] = deepcopy(INSTANCES['include_exclude_metrics']['include_metrics'])
    instance['metric_blacklist'] = deepcopy(INSTANCES['include_exclude_metrics']['exclude_metrics'])

    c1 = check(instance)
    c2 = check(INSTANCES['include_exclude_metrics'])
    assert c1.config_included_metrics == c2.config_included_metrics
    assert c1.config_excluded_metrics == c2.config_excluded_metrics


def test_success_fixture_included_metrics(aggregator, fixture_path, mock_http_response, check, dd_run_check):
    instance = INSTANCES['included_metrics']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/multiple_services'))
    dd_run_check(c)

    for metric in aggregator.metric_names:
        assert metric.startswith('envoy.cluster.')


def test_success_fixture_excluded_metrics(aggregator, fixture_path, mock_http_response, dd_run_check, check):
    instance = INSTANCES['excluded_metrics']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/multiple_services'))
    dd_run_check(c)

    for metric in aggregator.metric_names:
        assert not metric.startswith('envoy.cluster.')


def test_success_fixture_inclued_and_excluded_metrics(
    aggregator, fixture_path, mock_http_response, dd_run_check, check
):
    instance = INSTANCES['included_excluded_metrics']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/multiple_services'))
    dd_run_check(c)

    for metric in aggregator.metric_names:
        assert metric.startswith("envoy.cluster.") and not metric.startswith("envoy.cluster.out.")


def test_service_check(aggregator, fixture_path, mock_http_response, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/multiple_services'))
    dd_run_check(c)

    assert aggregator.service_checks(Envoy.SERVICE_CHECK_NAME)[0].status == Envoy.OK


def test_unknown(fixture_path, mock_http_response, dd_run_check, check):
    instance = INSTANCES['main']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/unknown_metrics'))
    dd_run_check(c)

    assert sum(c.unknown_metrics.values()) == 5


@pytest.mark.parametrize(
    'extra_config, expected_http_kwargs',
    [
        pytest.param(
            {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}, id="new auth config"
        ),
        pytest.param({'verify_ssl': True}, {'verify': True}, id="legacy ssl config True"),
        pytest.param({'verify_ssl': False}, {'verify': False}, id="legacy ssl config False"),
        pytest.param({}, {'verify': True}, id="legacy ssl config unset"),
    ],
)
def test_config(extra_config, expected_http_kwargs, check, dd_run_check):
    instance = deepcopy(INSTANCES['main'])
    instance.update(extra_config)
    check = check(instance)

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        dd_run_check(check)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://{}:8001/stats'.format(HOST), **http_wargs)


@pytest.mark.parametrize(
    'exception, log_call_parameters',
    [
        pytest.param(
            requests.exceptions.Timeout(),
            ('Envoy endpoint `%s` timed out after %s seconds', 'http://localhost:8001/server_info', (10.0, 10.0)),
            id="timeout",
        ),
        pytest.param(
            IndexError(),
            ('Error collecting Envoy version with url=`%s`. Error: %s', 'http://localhost:8001/server_info', ''),
            id="index error",
        ),
        pytest.param(
            requests.exceptions.RequestException('Req Exception'),
            (
                'Error collecting Envoy version with url=`%s`. Error: %s',
                'http://localhost:8001/server_info',
                'Req Exception',
            ),
            id="request exception",
        ),
    ],
)
def test_metadata_with_exception(
    datadog_agent, fixture_path, mock_http_response, check, exception, log_call_parameters
):
    instance = INSTANCES['main']
    check = check(instance)
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    with mock.patch('requests.get', side_effect=exception):
        check._collect_metadata()
        datadog_agent.assert_metadata_count(0)
        check.log.warning.assert_called_with(*log_call_parameters)


@pytest.mark.parametrize(
    'fixture_file, expected_version',
    [
        pytest.param(
            'server_info_' + FLAVOR,
            ENVOY_VERSION,
        ),
        pytest.param(
            'server_info_before_1_9',
            '1.8.0',
        ),
    ],
)
def test_metadata(datadog_agent, fixture_path, mock_http_response, check, fixture_file, expected_version):
    instance = INSTANCES['main']
    check = check(instance)
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    mock_http_response(file_path=fixture_path('./legacy/{}'.format(fixture_file)))

    check._collect_metadata()

    major, minor, patch = expected_version.split(".")
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': expected_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


def test_metadata_invalid(datadog_agent, fixture_path, mock_http_response, check):
    instance = INSTANCES['main']
    check = check(instance)
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    mock_http_response(file_path=fixture_path('./legacy/server_info_invalid'))
    check._collect_metadata()

    datadog_agent.assert_metadata('test:123', {})
    datadog_agent.assert_metadata_count(0)
    check.log.debug.assert_called_with('Version not matched.')


def test_metadata_not_collected(datadog_agent, check):
    instance = INSTANCES['collect_server_info']
    check = check(instance)
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    datadog_agent.assert_metadata('test:123', {})
    datadog_agent.assert_metadata_count(0)
    check.log.assert_not_called()


@pytest.mark.parametrize(
    ('fixture_file', 'metrics', 'standard_tags', 'additional_tags'),
    [
        (
            './legacy/stat_prefix',
            EXT_METRICS,
            ['cluster_name:foo', 'envoy_cluster:foo'],
            ['stat_prefix:bar'],
        ),
        (
            './legacy/rbac_metric.txt',
            RBAC_METRICS,
            ['stat_prefix:foo_buz_112'],
            ['shadow_rule_prefix:shadow_rule_prefix'],
        ),
    ],
    ids=[
        "stats_prefix_ext_auth",
        "rbac_prefix_shadow",
    ],
)
def test_stats_prefix_optional_tags(
    aggregator,
    fixture_path,
    mock_http_response,
    check,
    dd_run_check,
    fixture_file,
    metrics,
    standard_tags,
    additional_tags,
):
    instance = INSTANCES['main']
    standard_tags.append('endpoint:{}'.format(instance["stats_url"]))
    tags_prefix = standard_tags + additional_tags
    c = check(instance)
    mock_http_response(file_path=fixture_path(fixture_file))
    dd_run_check(c)

    # To ensure that this change didn't break the old behavior, both the value and the tags are asserted.
    # The fixture is created with a specific value and the EXT_METRICS list is done in alphabetical order
    # allowing for value to also be asserted
    for index, metric in enumerate(metrics):
        aggregator.assert_metric(
            metric,
            value=index + len(metrics),
            tags=tags_prefix,
        )
        aggregator.assert_metric(metric, value=index, tags=standard_tags)


def test_local_rate_limit_metrics(aggregator, fixture_path, mock_http_response, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/local_rate_limit.txt'))
    dd_run_check(c)

    for metric in LOCAL_RATE_LIMIT_METRICS:
        aggregator.assert_metric(metric)
        for tag in RATE_LIMIT_STAT_PREFIX_TAG:
            aggregator.assert_metric_has_tag(metric, tag, count=1)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_connection_limit_metrics(aggregator, fixture_path, mock_http_response, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)

    mock_http_response(file_path=fixture_path('./legacy/connection_limit.txt'))
    dd_run_check(c)
    for metric in CONNECTION_LIMIT_METRICS:
        for tag in CONNECTION_LIMIT_STAT_PREFIX_TAG:
            aggregator.assert_metric_has_tag(metric, tag, count=1)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
