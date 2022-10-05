# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import LEGACY_INSTANCE


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(aggregator, dd_agent_check):
    # Prevent the integration from failing before even running the check
    with pytest.raises(Exception):
        dd_agent_check(LEGACY_INSTANCE, rate=True)

    assert len(aggregator.service_check_names) == 0
