# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.elastic.metrics import (
    health_stats_for_version,
    node_os_stats_for_version,
    pshard_stats_for_version,
    stats_for_version,
)


@pytest.mark.unit
def test_stats_for_version():
    # v0.90
    metrics = stats_for_version([0, 90, 0])
    assert len(metrics) == 133

    # v0.90.5
    metrics = stats_for_version([0, 90, 5])
    assert len(metrics) == 134

    # v0.90.10
    metrics = stats_for_version([0, 90, 10])
    assert len(metrics) == 132

    # v1
    metrics = stats_for_version([1, 0, 0])
    assert len(metrics) == 140

    # v1.3.0
    metrics = stats_for_version([1, 3, 0])
    assert len(metrics) == 142

    # v1.4.0
    metrics = stats_for_version([1, 4, 0])
    assert len(metrics) == 162

    # v1.5.0
    metrics = stats_for_version([1, 5, 0])
    assert len(metrics) == 165

    # v1.6.0
    metrics = stats_for_version([1, 6, 0])
    assert len(metrics) == 173

    # v2
    metrics = stats_for_version([2, 0, 0])
    assert len(metrics) == 172

    # v2.1.0
    metrics = stats_for_version([2, 1, 0])
    assert len(metrics) == 177

    # v5
    metrics = stats_for_version([5, 0, 0])
    assert len(metrics) == 180

    # v6.3.0
    metrics = stats_for_version([6, 3, 0])
    assert len(metrics) == 180

    # v7.2.0
    metrics = stats_for_version([7, 2, 0])
    assert len(metrics) == 177


@pytest.mark.unit
def test_pshard_stats_for_version():
    # v0.90
    pshard_metrics = pshard_stats_for_version([0, 90, 0])
    assert len(pshard_metrics) == 23

    # v0.90.5
    pshard_metrics = pshard_stats_for_version([0, 90, 5])
    assert len(pshard_metrics) == 23

    # v0.90.10
    pshard_metrics = pshard_stats_for_version([0, 90, 10])
    assert len(pshard_metrics) == 23

    # v1
    pshard_metrics = pshard_stats_for_version([1, 0, 0])
    assert len(pshard_metrics) == 34

    # v1.3.0
    pshard_metrics = pshard_stats_for_version([1, 3, 0])
    assert len(pshard_metrics) == 34

    # v1.4.0
    pshard_metrics = pshard_stats_for_version([1, 4, 0])
    assert len(pshard_metrics) == 34

    # v1.5.0
    pshard_metrics = pshard_stats_for_version([1, 5, 0])
    assert len(pshard_metrics) == 34

    # v1.6.0
    pshard_metrics = pshard_stats_for_version([1, 6, 0])
    assert len(pshard_metrics) == 34

    # v2
    pshard_metrics = pshard_stats_for_version([2, 0, 0])
    assert len(pshard_metrics) == 34

    # v2.1.0
    pshard_metrics = pshard_stats_for_version([2, 1, 0])
    assert len(pshard_metrics) == 34

    # v5
    pshard_metrics = pshard_stats_for_version([5, 0, 0])
    assert len(pshard_metrics) == 34

    # v6.3.0
    pshard_metrics = pshard_stats_for_version([6, 3, 0])
    assert len(pshard_metrics) == 34

    # v7.2.0
    pshard_metrics = pshard_stats_for_version([7, 2, 0])
    assert len(pshard_metrics) == 36


@pytest.mark.unit
def test_health_stats_for_version():
    # v0.90
    metrics = health_stats_for_version([0, 90, 0])
    assert len(metrics) == 8

    # v0.90.5
    metrics = health_stats_for_version([0, 90, 5])
    assert len(metrics) == 8

    # v0.90.10
    metrics = health_stats_for_version([0, 90, 10])
    assert len(metrics) == 8

    # v1
    metrics = health_stats_for_version([1, 0, 0])
    assert len(metrics) == 8

    # v1.3.0
    metrics = health_stats_for_version([1, 3, 0])
    assert len(metrics) == 8

    # v1.4.0
    metrics = health_stats_for_version([1, 4, 0])
    assert len(metrics) == 8

    # v1.5.0
    metrics = health_stats_for_version([1, 5, 0])
    assert len(metrics) == 8

    # v1.6.0
    metrics = health_stats_for_version([1, 6, 0])
    assert len(metrics) == 8

    # v2
    metrics = health_stats_for_version([2, 0, 0])
    assert len(metrics) == 8

    # v2.1.0
    metrics = health_stats_for_version([2, 1, 0])
    assert len(metrics) == 8

    # v5
    metrics = health_stats_for_version([5, 0, 0])
    assert len(metrics) == 9

    # v6.3.0
    metrics = health_stats_for_version([6, 3, 0])
    assert len(metrics) == 9


@pytest.mark.unit
def test_node_os_stats_for_version():
    # v0.90
    metrics = node_os_stats_for_version([0, 90, 0])
    assert len(metrics) == 4

    # v0.90.5
    metrics = node_os_stats_for_version([0, 90, 5])
    assert len(metrics) == 4

    # v0.90.10
    metrics = node_os_stats_for_version([0, 90, 10])
    assert len(metrics) == 4

    # v1
    metrics = node_os_stats_for_version([1, 0, 0])
    assert len(metrics) == 6

    # v1.3.0
    metrics = node_os_stats_for_version([1, 3, 0])
    assert len(metrics) == 6

    # v1.4.0
    metrics = node_os_stats_for_version([1, 4, 0])
    assert len(metrics) == 6

    # v1.5.0
    metrics = node_os_stats_for_version([1, 5, 0])
    assert len(metrics) == 6

    # v1.6.0
    metrics = node_os_stats_for_version([1, 6, 0])
    assert len(metrics) == 6

    # v2
    metrics = node_os_stats_for_version([2, 0, 0])
    assert len(metrics) == 6

    # v2.1.0
    metrics = node_os_stats_for_version([2, 1, 0])
    assert len(metrics) == 6

    # v5
    metrics = node_os_stats_for_version([5, 0, 0])
    assert len(metrics) == 10

    # v6.3.0
    metrics = node_os_stats_for_version([6, 3, 0])
    assert len(metrics) == 10
