# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.pulsar import PulsarCheck

from .common import EXPECTED_METRICS, METRICS_URL, OPTIONAL_METRICS

pytestmark = [pytest.mark.e2e]


def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_service_check('pulsar.openmetrics.health', ServiceCheck.OK)

    for metric in EXPECTED_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, f'endpoint:{METRICS_URL}')

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()


def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True)

    aggregator.assert_metric('pulsar.topics_count', at_least=1)
    aggregator.assert_service_check('pulsar.openmetrics.health', ServiceCheck.OK, at_least=1)
    # In discovery mode, the endpoint tag is derived from the runtime-discovered
    # service host, not from the static host-mapped METRICS_URL used by test_check.
    # Validate discovered metrics via metadata instead of asserting a fixed endpoint tag.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, PulsarCheck)
