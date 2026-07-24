# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check: Any) -> None:
    # No explicit instance/config is passed: `ddev env start` already installed the Agent
    # config produced by `dd_environment` (the dynamic, free-port endpoint), so this reuses it.
    aggregator = dd_agent_check(rate=True)

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
