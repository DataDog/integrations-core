# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.scylla import ScyllaCheck

from .common import INSTANCE_DEFAULT_GROUPS, INSTANCE_DEFAULT_METRICS, get_metrics


def test_instance_default_check(aggregator, db_instance, mock_db_data):
    c = ScyllaCheck('scylla', {}, [db_instance])

    c.check(db_instance)

    for m in INSTANCE_DEFAULT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_instance_additional_check(aggregator, db_instance, mock_db_data):
    # add additional metric groups for validation
    additional_metrics = ['scylla.alien', 'scylla.sstables']

    instance = deepcopy(db_instance)
    instance['metric_groups'] = additional_metrics

    c = ScyllaCheck('scylla', {}, [instance])

    c.check(instance)

    metrics_to_check = get_metrics(INSTANCE_DEFAULT_GROUPS + additional_metrics)

    for m in metrics_to_check:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('scylla.prometheus.health', count=1)


def test_instance_invalid_group_check(aggregator, db_instance, mock_db_data):
    additional_metrics = ['scylla.bogus', 'scylla.sstables']

    instance = deepcopy(db_instance)
    instance['metric_groups'] = additional_metrics

    with pytest.raises(ConfigurationError):
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
