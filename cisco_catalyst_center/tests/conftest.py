# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Any, Callable, Iterator

import pytest

from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient

from .common import ScriptedHttp


@pytest.fixture
def instance() -> InstanceType:
    return {
        'catalyst_center_host': 'catalyst.example.com',
        'catalyst_center_username': 'observer',
        'catalyst_center_password': 'secret',
        'namespace': 'default',
    }


@pytest.fixture
def check(instance: InstanceType) -> CiscoCatalystCenterCheck:
    return CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])


@pytest.fixture
def http_script() -> list[Any]:
    """Overridden indirectly by the `respond` helpers."""
    return []


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Callable[[float], None]:
    """Freeze the clock the window arithmetic reads, and return a way to advance it.

    Time is a system boundary, and here it is the input under test. Two calls landing in the same
    millisecond are indistinguishable from a cycle whose window came out empty, so a test on the
    real clock would be asserting on how fast it happened to run.
    """
    current = {'seconds': 1_755_000_000.0}
    monkeypatch.setattr('datadog_checks.cisco_catalyst_center.check.time.time', lambda: current['seconds'])

    def advance(seconds: float) -> None:
        current['seconds'] += seconds

    return advance


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record backoff waits instead of performing them.

    Time is a system boundary, and a test that actually slept through a rate-limit backoff would
    take longer than the whole suite.
    """
    recorded: list[float] = []
    monkeypatch.setattr(
        'datadog_checks.cisco_catalyst_center.client.time.sleep', lambda seconds: recorded.append(seconds)
    )
    return recorded


@pytest.fixture
def client(instance: InstanceType, http_script: list[Any]) -> CatalystCenterClient:
    return CatalystCenterClient(instance, http=ScriptedHttp(http_script))


@pytest.fixture
def respond(client: CatalystCenterClient):
    """Reply to every request with the same payload."""

    def _respond(payload: Any) -> list[dict[str, Any]]:
        client.http = ScriptedHttp([payload])
        return client.http.requests

    return _respond


@pytest.fixture
def respond_sequence(client: CatalystCenterClient):
    """Reply with each payload in turn, repeating the last one once exhausted.

    Returns the live list of recorded requests so a test can assert on pagination parameters.
    """

    def _respond_sequence(payloads: list[Any]) -> list[dict[str, Any]]:
        client.http = ScriptedHttp(payloads)
        return client.http.requests

    return _respond_sequence


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[None]:
    # There are no E2E tests: Catalyst Center has no public container image, so there is nothing
    # to stand up. The fixture still has to exist -- CI runs `ddev env test` for every
    # integration, and the pytest plugin exits with NO E2E FIXTURE AVAILABLE when it is missing,
    # which fails the job. A no-op yield is the same thing guarddog, litellm and mac_audit_logs do.
    yield
