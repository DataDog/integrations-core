# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from . import common, metrics

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("dd_environment"),
]


def test_check(aggregator, check):
    service_check_tags = common._config_sc_tags(common.CONFIG)

    # get version and test v3 first.
    version = common._get_pdns_version()
    if version == 3:
        check.check(common.CONFIG)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        for metric in metrics.RATE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.OK, tags=service_check_tags)
        aggregator.assert_all_metrics_covered()

    elif version == 4:
        check.check(common.CONFIG_V4)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS + metrics.GAUGE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        for metric in metrics.RATE_METRICS + metrics.RATE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[], count=1)

        aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.OK, tags=service_check_tags)
        aggregator.assert_all_metrics_covered()
    else:
        aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.CRITICAL, tags=service_check_tags)


def test_tags(aggregator, check):
    version = common._get_pdns_version()

    tags = ['foo:bar']
    if version == 3:
        config = common.CONFIG.copy()
        config['tags'] = ['foo:bar']
        check.check(config)

        # Assert metrics v3
        for metric in metrics.GAUGE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

        for metric in metrics.RATE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

    elif version == 4:
        config = common.CONFIG_V4.copy()
        config['tags'] = ['foo:bar']
        check.check(config)

        # Assert metrics v3
        for metric in metrics.GAUGE_METRICS + metrics.GAUGE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

        for metric in metrics.RATE_METRICS + metrics.RATE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=tags, count=1)

    service_check_tags = common._config_sc_tags(common.CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.OK, tags=service_check_tags + tags)

    aggregator.assert_all_metrics_covered()


def test_bad_api_key(aggregator, check):
    with pytest.raises(Exception):
        check.check(common.BAD_API_KEY_CONFIG)

    service_check_tags = common._config_sc_tags(common.BAD_API_KEY_CONFIG)
    aggregator.assert_service_check('powerdns.recursor.can_connect', status=check.CRITICAL, tags=service_check_tags)
    assert len(aggregator._metrics) == 0
