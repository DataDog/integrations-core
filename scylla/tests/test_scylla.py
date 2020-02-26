# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base.errors import CheckException, ConfigurationError
from datadog_checks.scylla import ScyllaCheck

from .common import (
    INSTANCE_ADDITIONAL_GROUPS,
    INSTANCE_ADDITIONAL_METRICS,
    INSTANCE_DEFAULT_GROUPS,
    INSTANCE_DEFAULT_METRICS,
    get_metrics,
)


@pytest.mark.unit
def test_instance_default_check(aggregator, db_instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [db_instance])

    c.check(db_instance)

    for m in INSTANCE_DEFAULT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


@pytest.mark.unit
def test_instance_additional_check(aggregator, db_instance, mock_db_data):
    # add additional metric groups for validation
    additional_metric_groups = ['scylla.alien', 'scylla.sstables']

    instance = deepcopy(db_instance)
    instance['metric_groups'] = additional_metric_groups

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metric_groups)

    for m in metrics_to_check:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


@pytest.mark.unit
def test_instance_full_additional_check(aggregator, db_instance, mock_db_data):
    instance = deepcopy(db_instance)
    instance['metric_groups'] = INSTANCE_ADDITIONAL_GROUPS

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = INSTANCE_DEFAULT_METRICS + INSTANCE_ADDITIONAL_METRICS

    for m in metrics_to_check:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


@pytest.mark.unit
def test_instance_invalid_group_check(aggregator, db_instance, mock_db_data):
    additional_metric_groups = ['scylla.bogus', 'scylla.sstables']

    instance = deepcopy(db_instance)
    instance['metric_groups'] = additional_metric_groups

    with pytest.raises(ConfigurationError):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)


@pytest.mark.unit
def test_invalid_instance(aggregator, db_instance, mock_db_data):
    instance = deepcopy(db_instance)
    instance.pop('prometheus_url')

    with pytest.raises(CheckException):
        ScyllaCheck('scylla', {}, [instance])

    aggregator.assert_service_check('scylla.prometheus.health', count=0)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_instance_integration_check(aggregator, db_instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [db_instance])

    c.check(db_instance)

    for m in INSTANCE_DEFAULT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)
