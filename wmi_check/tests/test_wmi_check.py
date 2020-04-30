# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import logging

from . import common

log = logging.getLogger(__file__)


def test_basic_check(mock_proc_sampler, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tags'] = ["optional:tag1"]

    c = check(instance)
    c.check(instance)

    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['optional:tag1'], count=1)

    aggregator.assert_all_metrics_covered()


def test_tags(mock_proc_sampler, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tags'] = ["optional:tag1"]
    instance['constant_tags'] = ["instance:tag2"]
    c = check(instance)

    c.check(instance)

    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['optional:tag1', 'instance:tag2'], count=1)

    aggregator.assert_all_metrics_covered()


def test_invalid_class(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['class'] = 'Unix'
    c = check(instance)

    c.check(instance)

    # No metrics/service check
    aggregator.assert_all_metrics_covered()


def test_invalid_metrics(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['metrics'].append(['InvalidProperty', 'proc.will.not.be.reported', 'gauge'])
    c = check(instance)

    c.check(instance)
    # No metrics/service check
    aggregator.assert_all_metrics_covered()


def test_check(mock_disk_sampler, aggregator, check):
    c = check(copy.deepcopy(common.INSTANCE))
    c.check(common.WMI_CONFIG)

    for _, mname, _ in common.WMI_CONFIG['metrics']:
        aggregator.assert_metric(mname, tags=["foobar"], count=1)
        aggregator.assert_metric(mname, tags=["foobar"], count=1)

    aggregator.assert_all_metrics_covered()
