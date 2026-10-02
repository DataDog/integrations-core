# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Base check error handling must behave the same whether or not a check sets AGNOSTIC_HTTP."""

import re

import pytest
import requests

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.prometheus import PrometheusCheck
from datadog_checks.base.utils.http import RequestsWrapper

ENDPOINT = 'http://fake.endpoint:10055/metrics'


@pytest.fixture(params=[False, True], ids=['default', 'agnostic'])
def http_mode(request, monkeypatch, mocker):
    monkeypatch.setattr(AgentCheck, 'AGNOSTIC_HTTP', request.param)
    # Keeps SSL failures local instead of fetching intermediate certificates.
    mocker.patch.object(RequestsWrapper, 'fetch_intermediate_certs', return_value=[])


def _openmetrics_v1_check():
    check = OpenMetricsBaseCheck('openmetrics', {}, {})
    scraper_config = check.get_scraper_config(
        {'prometheus_url': ENDPOINT, 'namespace': 'test', 'metrics': ['*'], 'health_service_check': True}
    )
    return check, scraper_config


def _prometheus_check():
    check = PrometheusCheck('prometheus', {}, {}, {})
    check.NAMESPACE = 'test'
    check.health_service_check = True
    return check


def _openmetrics_v2_check(**options):
    instance = {'openmetrics_endpoint': ENDPOINT, 'namespace': 'test', 'metrics': ['.+'], **options}
    return OpenMetricsBaseCheckV2('test', {}, [instance])


@pytest.mark.usefixtures('http_mode')
def test_openmetrics_v1_ssl_error_skips_health_service_check(aggregator, mocker):
    mocker.patch('requests.Session.get', side_effect=requests.exceptions.SSLError('bad cert'))
    check, scraper_config = _openmetrics_v1_check()

    with pytest.raises(requests.exceptions.SSLError):
        check.poll(scraper_config)

    assert not aggregator.service_checks('test.prometheus.health')


@pytest.mark.usefixtures('http_mode')
def test_openmetrics_v1_error_status_reports_critical(aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check, scraper_config = _openmetrics_v1_check()

    with pytest.raises(requests.exceptions.HTTPError):
        check.poll(scraper_config)

    aggregator.assert_service_check('test.prometheus.health', status=AgentCheck.CRITICAL, count=1)


@pytest.mark.usefixtures('http_mode')
def test_prometheus_ssl_error_skips_health_service_check(aggregator, mocker):
    mocker.patch('requests.Session.get', side_effect=requests.exceptions.SSLError('bad cert'))
    check = _prometheus_check()

    with pytest.raises(requests.exceptions.SSLError):
        check.poll(ENDPOINT)

    assert not aggregator.service_checks('test.prometheus.health')


@pytest.mark.usefixtures('http_mode')
def test_prometheus_error_status_reports_critical(aggregator, mock_http_response):
    mock_http_response(status_code=503)
    check = _prometheus_check()

    with pytest.raises(requests.exceptions.HTTPError):
        check.poll(ENDPOINT)

    aggregator.assert_service_check('test.prometheus.health', status=AgentCheck.CRITICAL, count=1)


@pytest.mark.usefixtures('http_mode')
def test_openmetrics_v2_error_names_the_endpoint(dd_run_check, mock_http_response):
    mock_http_response(status_code=503)
    check = _openmetrics_v2_check()

    with pytest.raises(Exception, match=re.escape(f'There was an error scraping endpoint {ENDPOINT}: 503')):
        dd_run_check(check)


@pytest.mark.usefixtures('http_mode')
def test_openmetrics_v2_ignores_connection_errors_when_configured(dd_run_check, mocker):
    mocker.patch('requests.Session.get', side_effect=requests.exceptions.ConnectionError('refused'))
    check = _openmetrics_v2_check(ignore_connection_errors=True)

    dd_run_check(check)
