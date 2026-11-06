# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]

# The only metrics that should ever carry the ``infra_mode`` tag.
INFRA_MODE_METRICS = ("nutanix.host.count", "nutanix.vm.count")


@pytest.mark.parametrize(
    ("infrastructure_mode", "tag_expected"),
    [
        pytest.param("basic", True, id="basic mode adds infra_mode tag"),
        pytest.param("full", False, id="full mode does not add infra_mode tag"),
        pytest.param(None, False, id="unset mode does not add infra_mode tag"),
    ],
)
def test_infra_mode_tag(dd_run_check, aggregator, mock_instance, mock_http_get, infrastructure_mode, tag_expected):
    if infrastructure_mode is not None:
        mock_instance["infrastructure_mode"] = infrastructure_mode
    check = NutanixCheck("nutanix", {}, [mock_instance])
    dd_run_check(check)

    # In basic mode every count series carries infra_mode:basic; otherwise none do.
    for metric_name in INFRA_MODE_METRICS:
        aggregator.assert_metric(metric_name, at_least=1)
        for metric in aggregator.metrics(metric_name):
            has_tag = "infra_mode:basic" in metric.tags
            assert has_tag is tag_expected
            assert not any(tag.startswith("infra_mode:") and tag != "infra_mode:basic" for tag in metric.tags)

    # No metric other than the two count metrics should ever carry an infra_mode tag.
    for metric_name in aggregator.metric_names:
        if metric_name in INFRA_MODE_METRICS:
            continue
        for metric in aggregator.metrics(metric_name):
            assert not any(tag.startswith("infra_mode:") for tag in metric.tags)
