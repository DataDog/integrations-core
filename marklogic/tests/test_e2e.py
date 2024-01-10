# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import COMMON_TAGS, INSTANCE, assert_metrics, assert_service_checks


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    # type: (Any) -> None
    aggregator = dd_agent_check(INSTANCE, rate=True)

    assert_metrics(aggregator, COMMON_TAGS)

    aggregator.assert_all_metrics_covered()

    # Service checks
    assert_service_checks(aggregator, COMMON_TAGS, count=2)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
