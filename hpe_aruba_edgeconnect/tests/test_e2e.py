# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.hpe_aruba_edgeconnect import HpeArubaEdgeconnectCheck
from tests.test_unit import EXPECTED_METRIC_COUNTS, EXPECTED_VALUES

NS = 'hpe_aruba_edgeconnect'


@pytest.mark.e2e
def test_e2e(dd_agent_check, dd_run_check, aggregator, mocker, dd_get_state):
    dd_agent_check()

    instance_config = dd_get_state('e2e_instance')
    check = HpeArubaEdgeconnectCheck('hpe_aruba_edgeconnect', {}, [instance_config])
    check.load_configuration_models()

    mocker.patch.object(check, 'read_persistent_cache', return_value='99999940')
    mocker.patch.object(check, 'write_persistent_cache')

    dd_run_check(check)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for metric_name in EXPECTED_METRIC_COUNTS:
        aggregator.assert_metric(f'{NS}.{metric_name}')

    for metric_name, expected_value, tag_subset in EXPECTED_VALUES:
        full_name = f'{NS}.{metric_name}'
        aggregator.assert_metric(full_name, value=expected_value)
        if tag_subset:
            aggregator.assert_metric_has_tags(full_name, tag_subset)

    aggregator.assert_all_metrics_covered()
