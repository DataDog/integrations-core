# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck

from .common import CHECK, E2E_INIT_CONFIG, EXPECTED_METRICS, GLUSTER_VERSION


@pytest.mark.unit
def test_check(aggregator, instance, mock_gstatus_data):
    # type: (AggregatorStub, Dict[str, Any], str) -> None
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(aggregator, datadog_agent, instance):
    c = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    c.check_id = 'test:123'
    c.check(instance)
    major, minor, patch = c.parse_version(GLUSTER_VERSION)

    version_metadata = {
        'version.raw': GLUSTER_VERSION,
        'version.scheme': 'glusterfs',
        'version.major': major,
        'version.minor': minor,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(4)


@pytest.mark.unit
def test_parse_version(instance):
    c = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    major, minor, patch = c.parse_version('3.13.2')
    assert major == '3'
    assert minor == '13'
    assert patch == '2'
