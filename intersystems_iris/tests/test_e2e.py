# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import assert_metrics_match_metadata


@pytest.mark.e2e
def test_e2e(dd_agent_check: Any) -> None:
    # No explicit instance/config is passed: `ddev env start` already installed the Agent
    # config produced by `dd_environment` (the dynamic, free-port endpoint), so this reuses it.
    aggregator = dd_agent_check(rate=True)

    # The Docker environment auto-enables interoperability SAM sampling and starts a demo
    # production with traffic (see tests/docker/init/iris-init.sh), so the same single endpoint
    # exposes both the base families and the always-on `iris_interop_*` interface family. This
    # runs against the same standalone, non-mirrored container as the integration test, so the
    # gated families are excused here in the same way.
    assert_metrics_match_metadata(aggregator)

    aggregator.assert_service_check('intersystems_iris.openmetrics.health', ServiceCheck.OK)
