# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# flake8: noqa
import pytest

from datadog_checks.elastic.metrics import *


@pytest.mark.unit
def test_stats_for_version():
    # v0.90
    metrics = stats_for_version([0, 90, 0])
    assert len(metrics) == 123

    # v0.90.5
    metrics = stats_for_version([0, 90, 5])
    assert len(metrics) == 127

    # v0.90.10
    metrics = stats_for_version([0, 90, 10])
    assert len(metrics) == 131

    # v1
    metrics = stats_for_version([1, 0, 0])
    assert len(metrics) == 139

    # v1.3.0
    metrics = stats_for_version([1, 3, 0])
    assert len(metrics) == 141

    # v1.4.0
    metrics = stats_for_version([1, 4, 0])
    assert len(metrics) == 161

    # v1.5.0
    metrics = stats_for_version([1, 5, 0])
    assert len(metrics) == 164

    # v1.6.0
    metrics = stats_for_version([1, 6, 0])
    assert len(metrics) == 172

    # v2
    metrics = stats_for_version([2, 0, 0])
    assert len(metrics) == 184

    # v2.1.0
    metrics = stats_for_version([2, 1, 0])
    assert len(metrics) == 189

    # v5
    metrics = stats_for_version([5, 0, 0])
    assert len(metrics) == 192

    # v6.3.0
    metrics = stats_for_version([6, 3, 0])
    assert len(metrics) == 196


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
