# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# flake8: noqa
import pytest

from datadog_checks.elastic.metrics import *


@pytest.mark.unit
def test_get_for_version():
    # func must return 2 values, metrics and pshard_metrics
    assert len(get_for_version([])) == 2

    # v0.90
    metrics, pshard_metrics = get_for_version([0, 90, 0])
    assert len(metrics) == 123
    assert len(pshard_metrics) == 23

    # v0.90.5
    metrics, pshard_metrics = get_for_version([0, 90, 5])
    assert len(metrics) == 127
    assert len(pshard_metrics) == 23

    # v0.90.10
    metrics, pshard_metrics = get_for_version([0, 90, 10])
    assert len(metrics) == 131
    assert len(pshard_metrics) == 23

    # v1
    metrics, pshard_metrics = get_for_version([1, 0, 0])
    assert len(metrics) == 139
    assert len(pshard_metrics) == 34

    # v1.3.0
    metrics, pshard_metrics = get_for_version([1, 3, 0])
    assert len(metrics) == 141
    assert len(pshard_metrics) == 34

    # v1.4.0
    metrics, pshard_metrics = get_for_version([1, 4, 0])
    assert len(metrics) == 161
    assert len(pshard_metrics) == 34

    # v1.5.0
    metrics, pshard_metrics = get_for_version([1, 5, 0])
    assert len(metrics) == 164
    assert len(pshard_metrics) == 34

    # v1.6.0
    metrics, pshard_metrics = get_for_version([1, 6, 0])
    assert len(metrics) == 172
    assert len(pshard_metrics) == 34

    # v2
    metrics, pshard_metrics = get_for_version([2, 0, 0])
    assert len(metrics) == 184
    assert len(pshard_metrics) == 34

    # v2.1.0
    metrics, pshard_metrics = get_for_version([2, 1, 0])
    assert len(metrics) == 189
    assert len(pshard_metrics) == 34

    # v5
    metrics, pshard_metrics = get_for_version([5, 0, 0])
    assert len(metrics) == 192
    assert len(pshard_metrics) == 34

    # v6.3.0
    metrics, pshard_metrics = get_for_version([6, 3, 0])
    assert len(metrics) == 196
    assert len(pshard_metrics) == 34
