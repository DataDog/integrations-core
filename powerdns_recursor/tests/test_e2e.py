# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.powerdns_recursor import PowerDNSRecursorCheck

from . import common, metrics

pytestmark = [pytest.mark.e2e]


def test_powerdns_e2e(dd_agent_check):
    # get version and test v3 first.
    version = common._get_pdns_version()
    if version == 3:
        aggregator = dd_agent_check(common.CONFIG, rate=True)
        service_check_tags = common._config_sc_tags(common.CONFIG)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[])

        for metric in metrics.RATE_METRICS:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[])

        aggregator.assert_service_check(
            'powerdns.recursor.can_connect', status=PowerDNSRecursorCheck.OK, tags=service_check_tags
        )
        aggregator.assert_all_metrics_covered()

    elif version == 4:
        aggregator = dd_agent_check(common.CONFIG_V4, rate=True)
        service_check_tags = common._config_sc_tags(common.CONFIG_V4)

        # Assert metrics
        for metric in metrics.GAUGE_METRICS + metrics.GAUGE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[])

        for metric in metrics.RATE_METRICS + metrics.RATE_METRICS_V4:
            aggregator.assert_metric(metrics.METRIC_FORMAT.format(metric), tags=[])

        aggregator.assert_service_check(
            'powerdns.recursor.can_connect', status=PowerDNSRecursorCheck.OK, tags=service_check_tags
        )
        aggregator.assert_all_metrics_covered()
    else:
        raise Exception("Version not supported")
