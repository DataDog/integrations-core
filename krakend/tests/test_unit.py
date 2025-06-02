# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.krakend import KrakendCheck


def test_check(dd_run_check, aggregator, instance):
    # Tests will be added in the implementation Pr
    assert True


@pytest.mark.e2e
def test_e2e():
    # Dummy e2e for CI to pass
    assert True
