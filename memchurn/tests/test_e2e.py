# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

import pytest

from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check: Any, instance: InstanceType) -> None:
    aggregator = dd_agent_check(instance, rate=True)

    aggregator.assert_metric('memchurn.workers', value=instance['num_workers'])
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
