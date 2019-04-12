# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy

import pytest

from datadog_checks.fluentd import Fluentd

from .common import BAD_PORT, BAD_URL, CHECK_NAME, DEFAULT_INSTANCE, HOST

CHECK_GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']


@pytest.mark.usefixtures("dd_environment")
def test_fluentd(aggregator, check):
    instance = copy.deepcopy(DEFAULT_INSTANCE)
    instance["plugin_ids"] = ["plg1"]
    check.check(instance)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK, tags=sc_tags, count=1)
    for m in CHECK_GAUGES:
        aggregator.assert_metric('{0}.{1}'.format(CHECK_NAME, m), tags=['plugin_id:plg1'])

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_fluentd_exception(aggregator, check):
    instance = {"monitor_agent_url": BAD_URL, "plugin_ids": ["plg2"], "tags": ["test"]}

    with pytest.raises(Exception):
        check.check(instance)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:{}'.format(BAD_PORT), 'test']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.CRITICAL, tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_fluentd_with_tag_by_type(aggregator, check):
    instance = copy.deepcopy(DEFAULT_INSTANCE)
    instance["tag_by"] = "type"

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name)

        aggregator.assert_metric_has_tag_prefix(metric_name, 'type')

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK, tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_fluentd_with_tag_by_plugin_id(aggregator, check):
    instance = copy.deepcopy(DEFAULT_INSTANCE)
    instance["tag_by"] = "plugin_id"

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg1'])
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg2'])

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK, tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_fluentd_with_custom_tags(aggregator, check):
    instance = copy.deepcopy(DEFAULT_INSTANCE)
    custom_tags = ['test', 'tast:tast']
    instance["tags"] = custom_tags

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg1'] + custom_tags)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg2'] + custom_tags)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220'] + custom_tags
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK, tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()
