# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.boundary import BoundaryCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics

from .common import HEALTH_ENDPOINT, METRIC_ENDPOINT

pytestmark = [pytest.mark.e2e]


def test(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    custom_tags = instance['tags']

    health_tag = f'endpoint:{HEALTH_ENDPOINT}'
    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, tags=[health_tag, *custom_tags])

    metric_tag = f'endpoint:{METRIC_ENDPOINT}'
    aggregator.assert_service_check('boundary.openmetrics.health', ServiceCheck.OK, tags=[metric_tag, *custom_tags])

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric)

        aggregator.assert_metric_has_tag(metric, metric_tag)
        for tag in custom_tags:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_metrics_using_metadata(metadata_metrics)
    aggregator.assert_all_metrics_covered()


def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    aggregator.assert_service_check('boundary.controller.health', ServiceCheck.OK, at_least=1)
    aggregator.assert_service_check('boundary.openmetrics.health', ServiceCheck.OK, at_least=1)

    metadata_metrics = get_metadata_metrics()
    for metric in metadata_metrics:
        aggregator.assert_metric(metric)

    # Discovery-generated instances don't carry the static instance's custom `tags` config, and
    # the endpoint tag reflects the runtime-discovered container host rather than the static
    # HEALTH_ENDPOINT/METRIC_ENDPOINT used by the test above, so those tag-specific assertions
    # aren't repeated here.
    aggregator.assert_metrics_using_metadata(metadata_metrics)
    aggregator.assert_all_metrics_covered()


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, BoundaryCheck)
