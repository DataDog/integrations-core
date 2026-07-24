# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.iris import IrisCheck


@pytest.mark.integration
def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    dd_environment: dict[str, Any],
) -> None:
    instance = dd_environment['instances'][0]
    check = IrisCheck('iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    # The Docker environment auto-enables interoperability SAM sampling and starts a demo
    # production with traffic (see tests/docker/init/iris-init.sh), so the same single
    # endpoint exposes both the base families and the `iris_interop_*` families used to
    # populate the deduplicated metadata.csv catalog.
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )

    aggregator.assert_service_check('iris.openmetrics.health', ServiceCheck.OK)
