# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.scylla import ScyllaCheck
from tests.common import (
    FLAKY_METRICS,
    INSTANCE_ADDITIONAL_GROUPS,
    INSTANCE_ADDITIONAL_METRICS,
    INSTANCE_DEFAULT_GROUPS,
    INSTANCE_DEFAULT_METRICS,
    get_metrics,
)


def test_instance_default_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    check = ScyllaCheck('scylla', {}, [instance_legacy])

    dd_run_check(check)
    dd_run_check(check)

    for m in INSTANCE_DEFAULT_METRICS:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


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
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)


def test_instance_full_additional_check(aggregator, mock_db_data, dd_run_check, instance_legacy):
    inst = deepcopy(instance_legacy)
    inst['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    check = ScyllaCheck('scylla', {}, [inst])

    dd_run_check(check)
    dd_run_check(check)

    metrics_to_check = INSTANCE_DEFAULT_METRICS + INSTANCE_ADDITIONAL_METRICS

    for m in metrics_to_check:
        if m in FLAKY_METRICS:
            aggregator.assert_metric(m, at_least=0)
        else:
            aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', status=AgentCheck.OK)


def test_instance_invalid_group_check(aggregator, mock_db_data, instance_legacy):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    inst = deepcopy(instance_legacy)
    inst['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)


def test_invalid_instance(aggregator, mock_db_data, instance_legacy):
    inst = deepcopy(instance_legacy)
    inst.pop('prometheus_url')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [inst])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)
