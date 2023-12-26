# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
from six import PY2

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
    get_metrics,
    transform_metrics_omv2,
)


@pytest.mark.unit
def test_instance_default_check(aggregator, instance_legacy, mock_db_data):
    c = ScyllaCheck('scylla', {}, [instance_legacy])

    c.check(instance_legacy)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_instance_default_check_omv2(aggregator, instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance_legacy)

    for m in INSTANCE_DEFAULT_METRICS_V2:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_instance_additional_check(aggregator, instance_legacy, mock_db_data):
    # add additional metric groups for validation
    additional_metric_groups = ['scylla.alien', 'scylla.sstables']

    instance = deepcopy(instance_legacy)
    instance['metric_groups'] = additional_metric_groups

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metric_groups)

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_instance_additional_check_omv2(aggregator, instance, mock_db_data):
    # add additional metric groups for validation
    additional_metric_groups = ['scylla.alien', 'scylla.sstables']

    instance = deepcopy(instance)
    instance['metric_groups'] = additional_metric_groups

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = transform_metrics_omv2(get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metric_groups))

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', count=1)


@pytest.mark.unit
def test_instance_full_additional_check(aggregator, instance_legacy, mock_db_data):
    instance = deepcopy(instance_legacy)
    instance['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = INSTANCE_DEFAULT_METRICS + INSTANCE_ADDITIONAL_METRICS

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_instance_full_additional_check_omv2(aggregator, instance, mock_db_data):
    instance = deepcopy(instance)
    instance['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = INSTANCE_DEFAULT_METRICS_V2 + INSTANCE_ADDITIONAL_METRICS_V2

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', count=1)


@pytest.mark.unit
def test_instance_invalid_group_check(aggregator, instance_legacy, mock_db_data):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    instance = deepcopy(instance_legacy)
    instance['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_instance_invalid_group_check_omv2(aggregator, instance, mock_db_data):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    instance = deepcopy(instance)
    instance['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.openmetrics.health', count=0)


@pytest.mark.unit
def test_invalid_instance(aggregator, instance_legacy, mock_db_data):
    instance = deepcopy(instance_legacy)
    instance.pop('prometheus_url')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)


@pytest.mark.unit
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
def test_invalid_instance_omv2(aggregator, instance, mock_db_data):
    instance = deepcopy(instance)
    instance.pop('openmetrics_endpoint')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.openmetrics.health', count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check(aggregator, instance_legacy, mock_db_data):
    c = ScyllaCheck('scylla', {}, [instance_legacy])

    c.check(instance_legacy)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


@pytest.mark.integration
@pytest.mark.skipif(PY2, reason='OpenMetrics V2 is only available with Python 3')
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check_omv2(aggregator, instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    for m in INSTANCE_DEFAULT_METRICS_V2:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, count=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.openmetrics.health', count=1)
