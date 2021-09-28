# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.envoy import Envoy
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

from .common import ENVOY_VERSION, FLAVOR, HOST, INSTANCES

CHECK_NAME = 'envoy'


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_success(aggregator):
    instance = INSTANCES['main']
    c = Envoy(CHECK_NAME, {}, [instance])
    c.check(instance)

    metrics_collected = 0
    for metric in METRICS:
        collected_metrics = aggregator.metrics(METRIC_PREFIX + metric)
        if collected_metrics:
            expected_tags = [t for t in METRICS[metric]['tags'] if t]
            for tag_set in expected_tags:
                assert all(
                    all(any(tag in mt for mt in m.tags) for tag in tag_set) for m in collected_metrics if m.tags
                ), ('tags ' + str(expected_tags) + ' not found in ' + metric)
        metrics_collected += len(collected_metrics)
    assert metrics_collected >= 445


@pytest.mark.unit
def test_success_fixture(aggregator, fixture_path, mock_http_response):
    instance = INSTANCES['main']
    c = Envoy(CHECK_NAME, {}, [instance])

    response = mock_http_response(file_path=fixture_path('multiple_services')).return_value
    c.check(instance)

    metrics_collected = 0
    for metric in METRICS:
        metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

    num_metrics = len(response.content.decode().splitlines())
    num_metrics -= sum(c.unknown_metrics.values()) + sum(c.unknown_tags.values())
    assert 4481 <= metrics_collected == num_metrics


@pytest.mark.unit
def test_retrocompatible_config():
    instance = deepcopy(INSTANCES['main'])
    instance['metric_whitelist'] = deepcopy(INSTANCES['included_excluded_metrics']['included_metrics'])
    instance['metric_blacklist'] = deepcopy(INSTANCES['included_excluded_metrics']['excluded_metrics'])

    c1 = Envoy(CHECK_NAME, {}, [instance])
    c2 = Envoy(CHECK_NAME, {}, [INSTANCES['included_excluded_metrics']])
    assert c1.config_included_metrics == c2.config_included_metrics
    assert c1.config_excluded_metrics == c2.config_excluded_metrics


@pytest.mark.unit
def test_success_fixture_included_metrics(aggregator, fixture_path, mock_http_response):
    instance = INSTANCES['included_metrics']
    c = Envoy(CHECK_NAME, {}, [instance])

    mock_http_response(file_path=fixture_path('multiple_services'))
    c.check(instance)

    for metric in aggregator.metric_names:
        assert metric.startswith('envoy.cluster.')


@pytest.mark.unit
def test_success_fixture_excluded_metrics(aggregator, fixture_path, mock_http_response):
    instance = INSTANCES['excluded_metrics']
    c = Envoy(CHECK_NAME, {}, [instance])

    mock_http_response(file_path=fixture_path('multiple_services'))
    c.check(instance)

    for metric in aggregator.metric_names:
        assert not metric.startswith('envoy.cluster.')


@pytest.mark.unit
def test_success_fixture_inclued_and_excluded_metrics(aggregator, fixture_path, mock_http_response):
    instance = INSTANCES['included_excluded_metrics']
    c = Envoy(CHECK_NAME, {}, [instance])

    mock_http_response(file_path=fixture_path('multiple_services'))
    c.check(instance)

    for metric in aggregator.metric_names:
        assert metric.startswith("envoy.cluster.") and not metric.startswith("envoy.cluster.out.")


@pytest.mark.unit
def test_service_check(aggregator, fixture_path, mock_http_response):
    instance = INSTANCES['main']
    c = Envoy(CHECK_NAME, {}, [instance])

    mock_http_response(file_path=fixture_path('multiple_services'))
    c.check(instance)

    assert aggregator.service_checks(Envoy.SERVICE_CHECK_NAME)[0].status == Envoy.OK


@pytest.mark.unit
def test_unknown(fixture_path, mock_http_response):
    instance = INSTANCES['main']
    c = Envoy(CHECK_NAME, {}, [instance])

    mock_http_response(file_path=fixture_path('unknown_metrics'))
    c.check(instance)

    assert sum(c.unknown_metrics.values()) == 5


@pytest.mark.unit
@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'verify_ssl': True}, {'verify': True}),
        ("legacy ssl config False", {'verify_ssl': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': True}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(INSTANCES['main'])
    instance.update(extra_config)
    check = Envoy(CHECK_NAME, {}, instances=[instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(instance)

        http_wargs = dict(
            auth=mock.ANY,
            cert=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=mock.ANY,
            verify=mock.ANY,
            allow_redirects=mock.ANY,
        )
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://{}:8001/stats'.format(HOST), **http_wargs)


@pytest.mark.unit
def test_metadata(datadog_agent, fixture_path, mock_http_response):
    instance = INSTANCES['main']
    check = Envoy(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    with mock.patch('requests.get', side_effect=requests.exceptions.Timeout()):
        check._collect_metadata()
        datadog_agent.assert_metadata_count(0)
        check.log.warning.assert_called_with(
            'Envoy endpoint `%s` timed out after %s seconds', 'http://localhost:8001/server_info', (10.0, 10.0)
        )

    datadog_agent.reset()
    with mock.patch('requests.get', side_effect=IndexError()):
        check._collect_metadata()
        datadog_agent.assert_metadata_count(0)
        check.log.warning.assert_called_with(
            'Error collecting Envoy version with url=`%s`. Error: %s', 'http://localhost:8001/server_info', ''
        )

    datadog_agent.reset()
    with mock.patch('requests.get', side_effect=requests.exceptions.RequestException('Req Exception')):
        check._collect_metadata()
        datadog_agent.assert_metadata_count(0)
        check.log.warning.assert_called_with(
            'Error collecting Envoy version with url=`%s`. Error: %s',
            'http://localhost:8001/server_info',
            'Req Exception',
        )

    datadog_agent.reset()
    with mock_http_response(file_path=fixture_path('server_info_' + FLAVOR)):
        check._collect_metadata()

        major, minor, patch = ENVOY_VERSION.split('.')
        version_metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': ENVOY_VERSION,
        }

        datadog_agent.assert_metadata('test:123', version_metadata)
        datadog_agent.assert_metadata_count(len(version_metadata))

    datadog_agent.reset()
    with mock_http_response(file_path=fixture_path('server_info_before_1_9')):
        check._collect_metadata()

        expected_version = '1.8.0'
        major, minor, patch = expected_version.split('.')
        version_metadata = {
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.raw': expected_version,
        }

        datadog_agent.assert_metadata('test:123', version_metadata)
        datadog_agent.assert_metadata_count(len(version_metadata))

    datadog_agent.reset()
    with mock_http_response(file_path=fixture_path('server_info_invalid')):
        check._collect_metadata()

        datadog_agent.assert_metadata('test:123', {})
        datadog_agent.assert_metadata_count(0)
        check.log.debug.assert_called_with('Version not matched.')


@pytest.mark.unit
def test_metadata_not_collected(datadog_agent):
    instance = INSTANCES['collect_server_info']
    check = Envoy(CHECK_NAME, {}, [instance])
    check.check_id = 'test:123'
    check.log = mock.MagicMock()

    datadog_agent.assert_metadata('test:123', {})
    datadog_agent.assert_metadata_count(0)
    check.log.assert_not_called()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata_integration(aggregator, datadog_agent):
    instance = INSTANCES['main']
    c = Envoy(CHECK_NAME, {}, [instance])
    c.check_id = 'test:123'
    c.check(instance)

    major, minor, patch = ENVOY_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': ENVOY_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
