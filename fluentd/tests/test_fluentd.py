# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.fluentd import Fluentd

from .common import URL, BAD_URL, CHECK_NAME, HOST, BAD_PORT

CHECK_GAUGES = ['retry_count', 'buffer_total_queued_size', 'buffer_queue_length']


def test_fluentd(aggregator, spin_up_fluentd, check):
    instance = {
        "monitor_agent_url": URL,
        "plugin_ids": ["plg1"],
    }

    check.check(instance)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK,
                                    tags=sc_tags, count=1)
    for m in CHECK_GAUGES:
        aggregator.assert_metric('{0}.{1}'.format(CHECK_NAME, m), tags=['plugin_id:plg1'])

    aggregator.assert_all_metrics_covered()


def test_fluentd_exception(aggregator, spin_up_fluentd, check):
    instance = {
        "monitor_agent_url": BAD_URL,
        "plugin_ids": ["plg2"],
        "tags": ["test"]
    }

    with pytest.raises(Exception):
        check.check(instance)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:{}'.format(BAD_PORT), 'test']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.CRITICAL,
                                    tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_fluentd_with_tag_by_type(aggregator, spin_up_fluentd, check):
    instance = {
        "monitor_agent_url": URL,
        "tag_by": "type",
    }

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name)

        aggregator.assert_metric_has_tag_prefix(metric_name, 'type')

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK,
                                    tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_fluentd_with_tag_by_plugin_id(aggregator, spin_up_fluentd, check):
    instance = {
        "monitor_agent_url": URL,
        "tag_by": "plugin_id",
    }

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg1'])
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg2'])

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220']
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK,
                                    tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_fluentd_with_custom_tags(aggregator, spin_up_fluentd, check):
    custom_tags = ['test', 'tast:tast']

    instance = {
        "monitor_agent_url": URL,
        "tags": custom_tags
    }

    check.check(instance)

    for m in CHECK_GAUGES:
        metric_name = '{0}.{1}'.format(CHECK_NAME, m)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg1'] + custom_tags)
        aggregator.assert_metric(metric_name, tags=['plugin_id:plg2'] + custom_tags)

    sc_tags = ['fluentd_host:{}'.format(HOST), 'fluentd_port:24220'] + custom_tags
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Fluentd.OK,
                                    tags=sc_tags, count=1)

    aggregator.assert_all_metrics_covered()
