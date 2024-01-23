# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import METRICS, NON_PREDICTABLE_TAGS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_check(dd_run_check, aggregator, check, management_instance):
    dd_run_check(check(management_instance))

    for metric in METRICS:
        # Some tag values can't be predicted, pid for instance
        non_predictable_tags = [
            t.split(":")[0] for t in metric.get("tags", []) if t.split(":")[0] in NON_PREDICTABLE_TAGS
        ]
        expected_tags = [t for t in metric.get("tags", []) if t.split(":")[0] not in NON_PREDICTABLE_TAGS]
        expected_tags += [f"management_api_url:{management_instance['management_api_url']}"]

        aggregator.assert_metric(
            metric["name"],
            at_least=metric.get("at_least", 1),
        )

        for tag in expected_tags:
            aggregator.assert_metric_has_tag(metric["name"], tag)

        for tag in non_predictable_tags:
            aggregator.assert_metric_has_tag_prefix(metric["name"], tag)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert len(aggregator.events) == 0


def test_check_unknown_url(dd_run_check, aggregator, check, management_instance):

    management_instance["management_api_url"] = "http://unknown_host:12345"
    management_instance["timeout"] = 1  # speedup the test

    dd_run_check(check(management_instance))

    aggregator.assert_service_check("torchserve.management_api.health", AgentCheck.CRITICAL)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    assert len(aggregator.events) == 0
