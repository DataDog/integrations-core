# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.fluxcd import FluxcdCheck

from .common import EXPECTED_METRICS


@pytest.mark.parametrize("fluxcd_version", ["v1", "v2"])
def test_assert_metrics(dd_run_check, aggregator, check, request, fluxcd_version):
    _mock_response = request.getfixturevalue(f"mock_metrics_{fluxcd_version}")
    dd_run_check(check)
    for metric_name in EXPECTED_METRICS[fluxcd_version]:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_config():
    with pytest.raises(ConfigurationError, match="Input should be a valid string"):
        FluxcdCheck('fluxcd', {}, [{'openmetrics_endpoint': 2}]).load_configuration_models()
