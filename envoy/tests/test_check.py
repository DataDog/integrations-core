# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

from .common import DEFAULT_INSTANCE, ENVOY_VERSION, FLAKY_METRICS, PROMETHEUS_METRICS, requires_new_environment

pytestmark = [requires_new_environment]


SKIP_TAG_ASSERTION = [
    'listener.downstream_cx_total',  # Not all of these metrics contain the address label
]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, dd_run_check, check):
    c = check(DEFAULT_INSTANCE)

    dd_run_check(c)
    dd_run_check(c)

    for metric in PROMETHEUS_METRICS:
        formatted_metric = "envoy.{}".format(metric)
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(formatted_metric, at_least=0)
            continue
        aggregator.assert_metric(formatted_metric)

        collected_metrics = aggregator.metrics(METRIC_PREFIX + metric)
        legacy_metric = METRICS.get(metric)
        if collected_metrics and legacy_metric and metric not in SKIP_TAG_ASSERTION:
            expected_tags = [t for t in legacy_metric.get('tags', []) if t]
            for tag_set in expected_tags:
                assert all(
                    all(any(tag in mt for mt in m.tags) for tag in tag_set) for m in collected_metrics if m.tags
                ), ('tags ' + str(expected_tags) + ' not found in ' + formatted_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata_integration(dd_run_check, datadog_agent, check):
    c = check(DEFAULT_INSTANCE)
    c.check_id = 'test:123'
    dd_run_check(c)

    major, minor, patch = ENVOY_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': ENVOY_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
