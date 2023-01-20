# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.elastic.metrics import (
    health_stats_for_version,
    node_system_stats_for_version,
    pshard_stats_for_version,
    stats_for_version,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, jvm_rate, expected_metric_count',
    [
        pytest.param([0, 90, 0], False, 190, id='v0.90'),
        pytest.param([0, 90, 5], False, 193, id='v0.90.5'),
        pytest.param([0, 90, 10], False, 191, id='v0.90.10'),
        pytest.param([1, 0, 0], False, 199, id='v1'),
        pytest.param([1, 3, 0], False, 201, id='v1.3.0'),
        pytest.param([1, 4, 0], False, 227, id='v1.4.0'),
        pytest.param([1, 5, 0], False, 231, id='v1.5.0'),
        pytest.param([1, 6, 0], False, 239, id='v1.6.0'),
        pytest.param([2, 0, 0], False, 240, id='v2.0.0'),
        pytest.param([2, 1, 0], False, 247, id='v2.1.0'),
        pytest.param([5, 0, 0], False, 250, id='v5'),
        pytest.param([6, 3, 0], False, 250, id='v6.3.0'),
        pytest.param([7, 2, 0], False, 244, id='v7.2.0'),
        pytest.param([0, 90, 0], True, 190, id='v0.90'),
        pytest.param([0, 90, 5], True, 193, id='v0.90.5'),
        pytest.param([0, 90, 10], True, 195, id='v0.90.10'),
        pytest.param([1, 0, 0], True, 203, id='jmx-rate-v1'),
        pytest.param([1, 3, 0], True, 205, id='jmx-rate-v1.3.0'),
        pytest.param([1, 4, 0], True, 231, id='jmx-rate-v1.4.0'),
        pytest.param([1, 5, 0], True, 235, id='jmx-rate-v1.5.0'),
        pytest.param([1, 6, 0], True, 243, id='jmx-rate-v1.6.0'),
        pytest.param([2, 0, 0], True, 244, id='jmx-rate-v2.0.0'),
        pytest.param([2, 1, 0], True, 251, id='jmx-rate-v2.1.0'),
        pytest.param([5, 0, 0], True, 254, id='jmx-rate-v5'),
        pytest.param([6, 3, 0], True, 254, id='jmx-rate-v6.3.0'),
        pytest.param([7, 2, 0], True, 248, id='jmx-rate-v7.2.0'),
        pytest.param([7, 9, 0], True, 251, id='jmx-rate-v7.9.0'),
    ],
)
def test_stats_for_version(version, jvm_rate, expected_metric_count):
    metrics = stats_for_version(version, jvm_rate)
    assert len(metrics) == expected_metric_count


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, expected_metric_count',
    [
        pytest.param([0, 90, 0], 23, id='v0.90'),
        pytest.param([0, 90, 5], 23, id='v0.90.5'),
        pytest.param([0, 90, 10], 23, id='v0.90.10'),
        pytest.param([1, 0, 0], 34, id='v1'),
        pytest.param([1, 3, 0], 34, id='v1.3.0'),
        pytest.param([1, 4, 0], 34, id='v1.4.0'),
        pytest.param([1, 5, 0], 34, id='v1.5.0'),
        pytest.param([1, 6, 0], 34, id='v1.6.0'),
        pytest.param([2, 0, 0], 34, id='v2.0.0'),
        pytest.param([2, 1, 0], 34, id='v2.1.0'),
        pytest.param([5, 0, 0], 34, id='v5'),
        pytest.param([6, 3, 0], 34, id='v6.3.0'),
        pytest.param([7, 2, 0], 36, id='v7.2.0'),
        pytest.param([7, 9, 0], 36, id='v7.9.0'),
    ],
)
def test_pshard_stats_for_version(version, expected_metric_count):
    pshard_metrics = pshard_stats_for_version(version)
    assert len(pshard_metrics) == expected_metric_count


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, expected_metric_count',
    [
        pytest.param([0, 90, 0], 8, id='v0.90'),
        pytest.param([0, 90, 5], 8, id='v0.90.5'),
        pytest.param([0, 90, 10], 8, id='v0.90.10'),
        pytest.param([1, 0, 0], 8, id='v1'),
        pytest.param([1, 3, 0], 8, id='v1.3.0'),
        pytest.param([1, 4, 0], 8, id='v1.4.0'),
        pytest.param([1, 5, 0], 8, id='v1.5.0'),
        pytest.param([1, 6, 0], 8, id='v1.6.0'),
        pytest.param([2, 0, 0], 8, id='v2.0.0'),
        pytest.param([2, 1, 0], 8, id='v2.1.0'),
        pytest.param([5, 0, 0], 9, id='v5'),
        pytest.param([6, 3, 0], 9, id='v6.3.0'),
        pytest.param([7, 2, 0], 9, id='v7.2.0'),
        pytest.param([7, 9, 0], 9, id='v7.9.0'),
    ],
)
@pytest.mark.unit
def test_health_stats_for_version(version, expected_metric_count):
    metrics = health_stats_for_version(version)
    assert len(metrics) == expected_metric_count


@pytest.mark.unit
@pytest.mark.parametrize(
    'version, expected_metric_count',
    [
        pytest.param([0, 90, 0], 7, id='v0.90'),
        pytest.param([0, 90, 5], 7, id='v0.90.5'),
        pytest.param([0, 90, 10], 7, id='v0.90.10'),
        pytest.param([1, 0, 0], 9, id='v1'),
        pytest.param([1, 3, 0], 9, id='v1.3.0'),
        pytest.param([1, 4, 0], 9, id='v1.4.0'),
        pytest.param([1, 5, 0], 9, id='v1.5.0'),
        pytest.param([1, 6, 0], 9, id='v1.6.0'),
        pytest.param([2, 0, 0], 9, id='v2.0.0'),
        pytest.param([2, 1, 0], 9, id='v2.1.0'),
        pytest.param([5, 0, 0], 16, id='v5'),
        pytest.param([6, 3, 0], 16, id='v6.3.0'),
        pytest.param([7, 2, 0], 16, id='v7.2.0'),
        pytest.param([7, 9, 0], 16, id='v7.9.0'),
    ],
)
def test_node_system_stats_for_version(version, expected_metric_count):
    metrics = node_system_stats_for_version(version)
    assert len(metrics) == expected_metric_count
