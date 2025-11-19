# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.avi_vantage import AviVantageCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .conftest import ADMIN_TENANT_METRICS_FOLDER, MULTIPLE_TENANTS_METRICS_FOLDER, NO_TENANT_METRICS_FOLDER


@pytest.mark.unit
def test_check(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    check = AviVantageCheck('avi_vantage', {}, [unit_instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(NO_TENANT_METRICS_FOLDER):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_check_with_default_tenants(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    check = AviVantageCheck('avi_vantage', {}, [unit_instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(NO_TENANT_METRICS_FOLDER):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_check_with_empty_tenant_name(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    instance = deepcopy(unit_instance)
    instance["tenants"] = [""]
    check = AviVantageCheck('avi_vantage', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(NO_TENANT_METRICS_FOLDER):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_check_with_tenant_admin(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    instance = deepcopy(unit_instance)
    instance["tenants"] = ["admin"]
    check = AviVantageCheck('avi_vantage', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(ADMIN_TENANT_METRICS_FOLDER):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.unit
def test_check_with_multiple_tenant(mock_client, get_expected_metrics, aggregator, unit_instance, dd_run_check):
    instance = deepcopy(unit_instance)
    instance["tenants"] = ["admin", "tenant_a", "tenant_b"]
    check = AviVantageCheck('avi_vantage', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(MULTIPLE_TENANTS_METRICS_FOLDER):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
def test_integration(
    dd_environment, get_expected_metrics, aggregator, integration_instance, dd_run_check, datadog_agent
):
    check = AviVantageCheck('avi_vantage', {}, [integration_instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(NO_TENANT_METRICS_FOLDER, endpoint='http://localhost:5000/'):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    version_metadata = {
        'version.major': '20',
        'version.minor': '1',
        'version.patch': '5',
        'version.raw': '20.1.5',
        'version.scheme': 'semver',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.e2e
def test_e2e(dd_agent_check, integration_instance, get_expected_metrics):
    aggregator = dd_agent_check(integration_instance)

    aggregator.assert_service_check("avi_vantage.can_connect", AviVantageCheck.OK)
    for metric in get_expected_metrics(NO_TENANT_METRICS_FOLDER, endpoint='http://localhost:5000/'):
        aggregator.assert_metric(metric['name'], metric['value'], metric['tags'], metric_type=metric['type'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
