# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.calico import CalicoCheck

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    assert CalicoCheck.DEFAULT_METRIC_LIMIT == 0
