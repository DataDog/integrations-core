# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.intersystems_iris import IrisCheck

from .common import unconditional_metadata_metrics


@pytest.mark.integration
def test_check(
    dd_run_check: Callable[..., None],
    aggregator: AggregatorStub,
    dd_environment: dict[str, Any],
) -> None:
    instance = dd_environment['instances'][0]
    check = IrisCheck('intersystems_iris', {}, [instance])
    dd_run_check(check)
    dd_run_check(check)

    # The Docker environment auto-enables interoperability SAM sampling and starts a demo
    # production with traffic (see tests/docker/init/iris-init.sh), so this single endpoint
    # exposes the base families alongside the always-on `iris_interop_*` interface family.
    # Nothing may be submitted that metadata.csv does not declare.
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    # The container is a standalone, non-mirrored instance with no ECP peers, so the catalog's
    # topology-gated families cannot appear here; everything else it declares must have been
    # collected. See `common.py` for what is excused and why.
    aggregator.assert_metrics_using_metadata(
        unconditional_metadata_metrics(get_metadata_metrics()),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)
