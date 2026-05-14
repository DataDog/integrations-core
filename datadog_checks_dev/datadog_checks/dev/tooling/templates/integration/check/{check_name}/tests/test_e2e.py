{license_header}

from typing import Any

import pytest

from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check: Any, instance: InstanceType) -> None:
    aggregator = dd_agent_check(instance)

    # Assert every metric emitted is declared in metadata.csv with the correct type and unit,
    # and that every metric in metadata.csv was emitted at least once.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    # Assert no metric was emitted that wasn't covered by an assertion above.
    aggregator.assert_all_metrics_covered()

    # Other useful assertions to consider for end-to-end coverage:
    # from datadog_checks.base.constants import ServiceCheck
    # aggregator.assert_service_check('{check_name}.can_connect', ServiceCheck.OK)
    # aggregator.assert_metric('{check_name}.<metric>', value=1.23, count=1, tags=['foo:bar'])
    # aggregator.assert_metric_has_tag('{check_name}.<metric>', 'env:prod')
    # aggregator.assert_metric_has_tag_prefix('{check_name}.<metric>', 'host:')
