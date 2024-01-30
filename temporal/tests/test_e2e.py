# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.temporal import TemporalCheck

from .common import TAGS

pytestmark = [pytest.mark.e2e]


def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for metric in get_metadata_metrics():
        aggregator.assert_metric(name=metric, at_least=0, tags=TAGS)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_e2e_service_checks(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    aggregator.assert_service_check(
        "temporal.server.openmetrics.health",
        status=TemporalCheck.OK,
        tags=TAGS,
    )
