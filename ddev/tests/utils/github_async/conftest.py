# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from tests.helpers.clock import FakeClock, advance_clock_on_sleep


@pytest.fixture
def instant_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the wait between retries, so a test that exhausts a policy costs no wall-clock time.

    stamina sleeps through ``asyncio.sleep``, which this replaces with a fake clock advance.
    """
    advance_clock_on_sleep(FakeClock(), monkeypatch)
