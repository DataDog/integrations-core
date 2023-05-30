# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.envoy.metrics import PROMETHEUS_METRICS_MAP

pytestmark = [pytest.mark.unit]


def test_unique_metrics():
    duplicated_metrics = set()

    for value in PROMETHEUS_METRICS_MAP.values():
        # We only have string with envoy so far
        assert isinstance(value, str)
        assert value not in duplicated_metrics, "metric `{}` already declared".format(value)
        duplicated_metrics.add(value)
