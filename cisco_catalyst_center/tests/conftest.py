# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Any, Iterator

import pytest

from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient

AUTH_PATH = '/dna/system/api/v1/auth/token'


class _Response:
    """Minimal stand-in for a ``requests.Response``."""

    def __init__(self, payload: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {'x-correlation-id': 'test-correlation-id', **(headers or {})}

    def json(self) -> Any:
        return self._payload


class ScriptedHttp:
    """Fake HTTP layer that replays a script and records what was asked of it.

    This is the only mock in the client tests. It sits exactly at the network boundary, so
    everything above it -- envelope unwrapping, pagination arithmetic, token lifecycle -- runs
    for real.
    """

    def __init__(self, script: list[Any]) -> None:
        self._script = list(script)
        self.requests: list[dict[str, Any]] = []
        self.auth_calls = 0

    #: Returned once the script is exhausted. A fake that replayed its last payload forever would
    #: make any collection whose size is an exact multiple of the page limit paginate endlessly --
    #: which is a defect in the fake, not in the client, since a real appliance answers the
    #: follow-up page with an empty list.
    EXHAUSTED = {'response': [], 'version': '1.0'}

    #: The analytics endpoints are POST and answer with an object, not a list, and every slot in
    #: it is null rather than empty when there is no data. A single exhaustion payload cannot
    #: stand in for both shapes, so the fake mirrors the one the verb actually returns.
    EXHAUSTED_OBJECT = {
        'response': {'attributes': None, 'aggregateAttributes': None, 'groups': None},
        'page': {'limit': 100, 'count': 0},
        'version': '1.0',
    }

    def _next(self, exhausted: Any = None) -> _Response:
        item = self._script.pop(0) if self._script else (exhausted or self.EXHAUSTED)
        if isinstance(item, dict) and 'status_code' in item and 'json' in item:
            return _Response(item['json'], item['status_code'], item.get('headers'))
        return _Response(item)

    def get(self, url: str, params: dict[str, Any] | None = None, **options: Any) -> _Response:
        self.requests.append({'url': url, 'params': params or {}, 'extra_headers': options.get('extra_headers', {})})
        return self._next()

    def post(self, url: str, **options: Any) -> _Response:
        if url.endswith(AUTH_PATH):
            self.auth_calls += 1
            return _Response({'Token': f'token-{self.auth_calls}'})
        self.requests.append(
            {
                'url': url,
                'params': options.get('params') or {},
                'json': options.get('json'),
                'extra_headers': options.get('extra_headers', {}),
            }
        )
        return self._next(self.EXHAUSTED_OBJECT)


class ViewRoutedHttp(ScriptedHttp):
    """Serves a different payload depending on the ``view`` query parameter.

    The interfaces endpoint returns a different field set per view, so a collector that reads
    several views issues several calls. Routing on the parameter keeps the test honest about
    which call produced which fields.
    """

    def __init__(self, by_view: dict[str | None, Any]) -> None:
        super().__init__([])
        self._by_view = by_view

    def get(self, url: str, params: dict[str, Any] | None = None, **options: Any) -> _Response:
        params = params or {}
        self.requests.append({'url': url, 'params': params, 'extra_headers': options.get('extra_headers', {})})
        return _Response(self._by_view[params.get('view')])


@pytest.fixture
def check_instance() -> InstanceType:
    return {
        'catalyst_center_host': 'catalyst.example.com',
        'catalyst_center_username': 'observer',
        'catalyst_center_password': 'secret',
        'namespace': 'default',
    }


@pytest.fixture
def http_script() -> list[Any]:
    """Overridden indirectly by the ``respond`` helpers."""
    return []


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
def client(check_instance: InstanceType, http_script: list[Any]) -> CatalystCenterClient:
    return CatalystCenterClient(check_instance, http=ScriptedHttp(http_script))


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
    # No containerised environment yet. Catalyst Center has no public image; the E2E story is a
    # small fake server, which lands with the first release rather than the proof of concept.
    yield


@pytest.fixture
def instance(check_instance: InstanceType) -> InstanceType:
    return check_instance
