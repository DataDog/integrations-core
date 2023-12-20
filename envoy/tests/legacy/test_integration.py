# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

from .common import ENVOY_VERSION, EXT_METRICS, INSTANCES, RBAC_METRICS

CHECK_NAME = 'envoy'
UNIQUE_METRICS = EXT_METRICS + RBAC_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_success(aggregator, check, dd_run_check):
    instance = INSTANCES['main']
    c = check(instance)
    dd_run_check(c)

    metrics_collected = 0
    for metric in METRICS:
        collected_metrics = aggregator.metrics(METRIC_PREFIX + metric)
        # The ext_auth and rbac metrics are excluded because the stats_prefix is not always present.
        # They're tested in a different test.
        if collected_metrics and collected_metrics[0].name not in UNIQUE_METRICS:
            expected_tags = [t for t in METRICS[metric]['tags'] if t]
            for tag_set in expected_tags:
                # Iterate over the expected tags and check that they're present in the collected_metric's tags.
                # We iterate over each collected metric and we see if the metric has more than 1 tag. If it does, we
                # iterate over each tag attached to the metric to see if the tags are in the tag_set of expected_tags.
                # Since an endpoint tag is added to each metric, checking for the metric specific tags parsed from the
                # metric, should only be done if the metric has more tags than just the endpoint tag.
                assert all(
                    all(any(tag in mt for mt in m.tags) for tag in tag_set)
                    for m in collected_metrics
                    if len(m.tags) > 1
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
