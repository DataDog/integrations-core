# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.scylla import ScyllaCheck

from .common import (
    FLAKY_METRICS,
    INSTANCE_ADDITIONAL_GROUPS,
    INSTANCE_ADDITIONAL_METRICS,
    INSTANCE_ADDITIONAL_METRICS_V2,
    INSTANCE_DEFAULT_GROUPS,
    INSTANCE_DEFAULT_METRICS,
    INSTANCE_DEFAULT_METRICS_V2,
    bucket_metrics,
    get_metrics,
    transform_metrics_omv2,
)


@pytest.mark.unit
def test_instance_default_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    check = ScyllaCheck('scylla', {}, [instance_legacy])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_instance_default_check_omv2(aggregator, mock_db_data, dd_run_check, instance):
    check = ScyllaCheck('scylla', {}, [instance])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS_V2:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_instance_additional_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    # add additional metric groups for validation
    additional_metric_groups = ['scylla.alien', 'scylla.sstables']

    inst = deepcopy(instance_legacy)
    inst['metric_groups'] = additional_metric_groups

    check = ScyllaCheck('scylla', {}, [inst])

    dd_run_check(check)
    dd_run_check(check)

    metrics_to_check = get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metric_groups)

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.unit
def test_instance_additional_check_omv2(aggregator, mock_db_data, dd_run_check, instance):
    # add additional metric groups for validation
    additional_metric_groups = ['scylla.alien', 'scylla.sstables']

    inst = deepcopy(instance)
    inst['metric_groups'] = additional_metric_groups

    check = ScyllaCheck('scylla', {}, [inst])

    dd_run_check(check)
    dd_run_check(check)

    metrics_to_check = get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metric_groups)
    transformed_metrics = transform_metrics_omv2(metrics_to_check) + bucket_metrics

    for m in transformed_metrics:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m) 

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.OK)


@pytest.mark.unit
def test_instance_full_additional_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    inst = deepcopy(instance_legacy)
    inst['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    check = ScyllaCheck('scylla', {}, [inst])

    dd_run_check(check)
    dd_run_check(check)

    metrics_to_check = INSTANCE_DEFAULT_METRICS + INSTANCE_ADDITIONAL_METRICS

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.unit
def test_instance_full_additional_check_omv2(aggregator, mock_db_data, dd_run_check, instance):
    inst = deepcopy(instance)
    inst['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    check = ScyllaCheck('scylla', {}, [inst])

    dd_run_check(check)
    dd_run_check(check)

    metrics_to_check = INSTANCE_DEFAULT_METRICS + INSTANCE_ADDITIONAL_METRICS
    transformed_metrics = transform_metrics_omv2(metrics_to_check) + bucket_metrics

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.OK)


@pytest.mark.unit
def test_instance_invalid_group_check(aggregator, mock_db_data, instance_legacy):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    inst = deepcopy(instance_legacy)
    inst['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.CRITICAL)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.unit
def test_instance_invalid_group_check_omv2(aggregator, mock_db_data, instance):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    inst = deepcopy(instance)
    inst['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.CRITICAL)


@pytest.mark.unit
def test_invalid_instance(aggregator, instance_legacy, mock_db_data):
    inst = deepcopy(instance_legacy)
    inst.pop('prometheus_url')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.CRITICAL)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.unit
def test_invalid_instance_omv2(aggregator, instance, mock_db_data):
    inst = deepcopy(instance)
    inst.pop('openmetrics_endpoint')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.CRITICAL)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    check = ScyllaCheck('scylla', {}, [instance_legacy])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)


@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check_omv2(aggregator, mock_db_data, dd_run_check, instance):
    check = ScyllaCheck('scylla', {}, [instance])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS_V2:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', status=AgentCheck.OK) 
