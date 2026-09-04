# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from typing import Any

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.intersystems_iris import IrisCheck

from .common import assert_healthy_scrape


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
    assert_healthy_scrape(aggregator)
