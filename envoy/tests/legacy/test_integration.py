# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

from .common import ENVOY_VERSION, EXT_METRICS, INSTANCES

CHECK_NAME = 'envoy'

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_success(aggregator, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)
    dd_run_check(c)

    metrics_collected = 0
    for metric in METRICS:
        collected_metrics = aggregator.metrics(METRIC_PREFIX + metric)
        # The ext_auth metrics are excluded because the stats_prefix is not always present.
        # They're tested in a different test.
        if collected_metrics and collected_metrics[0].name not in EXT_METRICS:
            expected_tags = [t for t in METRICS[metric]['tags'] if t]
            for tag_set in expected_tags:
                assert all(
                    all(any(tag in mt for mt in m.tags) for tag in tag_set) for m in collected_metrics if m.tags
                ), ('tags ' + str(expected_tags) + ' not found in ' + metric)
        metrics_collected += len(collected_metrics)
    assert metrics_collected >= 445

    metadata_metrics = get_metadata_metrics()
    # Metric that has a different type in legacy
    metadata_metrics['envoy.cluster.upstream_cx_tx_bytes_total']['metric_type'] = 'count'

    aggregator.assert_metrics_using_metadata(metadata_metrics)


def test_metadata_integration(datadog_agent, check):
    instance = INSTANCES['main']
    c = check(instance)
    c.check_id = 'test:123'
    c.check(instance)

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
