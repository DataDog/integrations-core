# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.glusterfs import GlusterfsCheck

from .common import CHECK, E2E_INIT_CONFIG, EXPECTED_METRICS

pytestmark = pytest.mark.unit


def test_check(aggregator, instance, mock_gstatus_data):
    check = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    check.check(instance)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_parse_version(instance):
    c = GlusterfsCheck(CHECK, E2E_INIT_CONFIG, [instance])
    major, minor, patch = c.parse_version('3.13.2')
    assert major == '3'
    assert minor == '13'
    assert patch == '2'
