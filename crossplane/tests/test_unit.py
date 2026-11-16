# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Callable

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.crossplane import CrossplaneCheck


def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    instance: InstanceType,
) -> None:
    check = CrossplaneCheck('crossplane', {}, [instance])
    dd_run_check(check)

    # Assert every metric emitted is declared in metadata.csv with the correct type and unit,
    # and that every metric in metadata.csv was emitted.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    # The following are useful assertions to help new users get started.

    # Assert a specific metric was emitted with a specific value, count, and tag set.
    # aggregator.assert_metric('crossplane.<metric>', value=1.23, count=1, tags=['foo:bar'])

    # Assert a metric carries a specific tag (exact match) or any tag with a given prefix.
    # aggregator.assert_metric_has_tag('crossplane.<metric>', 'env:prod')
    # aggregator.assert_metric_has_tag_prefix('crossplane.<metric>', 'host:')

    # Assert a service check was emitted with a specific status.
    # from datadog_checks.base.constants import ServiceCheck
    # aggregator.assert_service_check('crossplane.can_connect', ServiceCheck.OK, count=1)

    # Assert nothing was emitted that wasn't covered by an assertion above.
    aggregator.assert_all_metrics_covered()
