# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.fly_io import FlyIoCheck

from .metrics import (
    ALL_REST_METRICS,
    APP_UP_METRICS,
    MACHINE_COUNT_METRICS,
    MACHINE_GUEST_METRICS,
    MACHINE_INIT_METRICS,
    MOCKED_PROMETHEUS_METRICS,
    PROMETHEUS_METRICS_NO_HOST,
    PROMETHEUS_METRICS_ONE_HOST,
    VOLUME_METRICS,
)


@pytest.mark.usefixtures('mock_http_get')
def test_check(dd_run_check, aggregator, instance):
    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in PROMETHEUS_METRICS_ONE_HOST:
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")

    for metric in PROMETHEUS_METRICS_NO_HOST:
        aggregator.assert_metric(metric, at_least=1, hostname=None)

    for metric in ALL_REST_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=1)
    aggregator.assert_metric('fly_io.machines_api.up', value=1, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_http_get')
def test_no_machines_endpoint(dd_run_check, aggregator, instance):
    no_rest_api = copy.deepcopy(instance)
    del no_rest_api['machines_api_endpoint']

    check = FlyIoCheck('fly_io', {}, [no_rest_api])
    dd_run_check(check)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in PROMETHEUS_METRICS_ONE_HOST:
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")

    for metric in PROMETHEUS_METRICS_NO_HOST:
        aggregator.assert_metric(metric, at_least=1, hostname=None)

    for metric in ALL_REST_METRICS:
        aggregator.assert_metric(metric, count=0)

    aggregator.assert_service_check('fly_io.openmetrics.health', ServiceCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_app_metrics(dd_run_check, aggregator, instance, caplog):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    for metric in APP_UP_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])

    for metric in MACHINE_COUNT_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {'http_error': {'/v1/apps': MockResponse(status_code=500)}},
            id='500',
        ),
        pytest.param(
            {'http_error': {'/v1/apps': MockResponse(status_code=404)}},
            id='404',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_exception(dd_run_check, instance, aggregator):
    check = FlyIoCheck('fly_io', {}, [instance])
    with pytest.raises(Exception, match=r'requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_metric("fly_io.machines_api.up", value=0)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {
                'http_error': {
                    '/v1/apps/example-app-1/machines': MockResponse(json_data=[{'state': 'started', 'config': None}])
                }
            },
            id='malformed response',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_bad_response_exception(dd_run_check, instance, aggregator, caplog):
    caplog.set_level(logging.ERROR)
    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)

    assert (
        "Encountered an Exception in '_collect_machines_for_app' [<class 'AttributeError'>]: "
        "'NoneType' object has no attribute 'get'" in caplog.text
    )

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in VOLUME_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {'http_error': {'/v1/apps/example-app-1/volumes': MockResponse(status_code=404)}},
            id='http error',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_http_error_exception(dd_run_check, instance, aggregator, caplog):
    caplog.set_level(logging.DEBUG)
    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)

    assert (
        "Encountered a RequestException in '_collect_volumes_for_app' [<class 'requests.exceptions.HTTPError'>]: "
        "404 Client Error: None for url: None" in caplog.text
    )

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric(metric, at_least=1, hostname="708725eaa12297")
        aggregator.assert_metric(metric, at_least=1, hostname="20976671ha2292")
        aggregator.assert_metric(metric, at_least=1, hostname="119dc024cbf534")

    for metric in MACHINE_INIT_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])


@pytest.mark.usefixtures("mock_http_get")
def test_external_host_tags(instance, datadog_agent, dd_run_check):
    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    datadog_agent.assert_external_tags(
        '32601eaad60025',
        {
            'fly_io': [
                'fly_org:test',
                'app_name:example-app-1',
                'app_id:o7vx1kl85749k3f1',
                'instance_id:01AP4Y49KSI6PG1H7KPKJN5GF',
                'machine_region:ewr',
                'fly_platform_version:v2',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        '09201eeed60025',
        {
            'fly_io': [
                'fly_org:test',
                'app_name:example-app-1',
                'app_id:o7vx1kl85749k3f1',
                'instance_id:POSJ7Y49KSI6PG1H7KPKJN5IK',
                'machine_region:ewr',
                'fly_platform_version:v2',
            ]
        },
    )


@pytest.mark.parametrize(
    ('mock_http_get, log_lines'),
    [
        pytest.param(
            {'http_error': {'/v1/apps/example-app-2': MockResponse(status_code=404)}},
            ['RequestException in \'_get_app_status\' [<class \'requests.exceptions.HTTPError\'>]: 404'],
            id='one app',
        ),
        pytest.param(
            {
                'http_error': {
                    '/v1/apps/example-app-1': MockResponse(status_code=404),
                    '/v1/apps/example-app-2': MockResponse(status_code=500),
                }
            },
            [
                'RequestException in \'_get_app_status\' [<class \'requests.exceptions.HTTPError\'>]: 404',
                'RequestException in \'_get_app_status\' [<class \'requests.exceptions.HTTPError\'>]: 500',
            ],
            id='two apps',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_app_status_failed(dd_run_check, aggregator, instance, caplog, log_lines):

    check = FlyIoCheck('fly_io', {}, [instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    aggregator.assert_metric(
        'fly_io.app.count',
        tags=[
            'app_id:4840jpkjkxo1ei63',
            'app_name:example-app-2',
            'app_network:default',
            'app_status:None',
            'fly_org:test',
        ],
    )

    app_1_tags = ['app_id:o7vx1kl85749k3f1', 'app_name:example-app-1', 'app_network:default', 'fly_org:test']

    if len(log_lines) == 2:
        app_1_tags.append('app_status:None')
    else:
        app_1_tags.append('app_status:deployed')

    aggregator.assert_metric('fly_io.app.count', tags=app_1_tags)

    for log_line in log_lines:
        assert log_line in caplog.text


@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_machine_guest_metrics(dd_run_check, aggregator, instance):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    for metric in MACHINE_GUEST_METRICS:
        aggregator.assert_metric(
            metric['name'], metric['value'], count=metric['count'], tags=metric['tags'], hostname=metric['hostname']
        )


@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_machine_init_metrics(dd_run_check, aggregator, instance):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    for metric in MACHINE_INIT_METRICS:
        aggregator.assert_metric(
            metric['name'], metric['value'], count=metric['count'], tags=metric['tags'], hostname=metric['hostname']
        )


@pytest.mark.usefixtures('mock_http_get')
def test_rest_api_volume_metrics(dd_run_check, aggregator, instance):

    check = FlyIoCheck('fly_io', {}, [instance])
    dd_run_check(check)
    for metric in VOLUME_METRICS:
        aggregator.assert_metric(metric['name'], metric['value'], count=metric['count'], tags=metric['tags'])
