# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from typing import Any

import pytest

from datadog_checks.base.utils.http import RequestsWrapper

from .common import INSTANCE
from .fake_panos import FakePanos


@pytest.fixture(scope='session')
def dd_environment():
    # Lab and docker environments are added in a later task.
    yield


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(INSTANCE)


@pytest.fixture(autouse=True)
def fake_panos(monkeypatch, datadog_agent) -> FakePanos:
    """Serve every HTTP POST from the fake PAN-OS API, so no unit test reaches the network.

    Requesting `datadog_agent` resets the stubbed persistent cache between tests.
    """
    fake = FakePanos()
    monkeypatch.setattr(RequestsWrapper, 'post', lambda _self, url, **options: fake.post(url, **options))
    return fake
