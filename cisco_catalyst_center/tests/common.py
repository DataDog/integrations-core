# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared test helpers.

Fixtures live in two directories and the split is deliberate:

`captured/`
    Verbatim responses recorded from the Cisco DevNet always-on sandbox. Real values.

`wireless_synthetic/`
    Access point and radio payloads. The *keys* are generated from Cisco's published OpenAPI
    schema and are checked against it by `test_spec_conformance.py`. The *values* are
    hand-chosen, because Cisco's own schema examples are not physically plausible -- the
    example for `RadioKpi.noise` is `10` on a field documented in dBm, where a real noise
    floor is around -90. Never assert that a synthetic value matches a real controller.

Mutations are expressed as code via `with_value()`, never as hand-edited JSON, so that a
reviewer can always tell a recording from an alteration.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from datadog_checks.base.types import InstanceType
from datadog_checks.cisco_catalyst_center.client import CatalystCenterClient

FIXTURE_ROOT = Path(__file__).parent / 'fixtures'
CAPTURED_DIR = FIXTURE_ROOT / 'captured'
WIRELESS_SYNTHETIC_DIR = FIXTURE_ROOT / 'wireless_synthetic'


def load_captured(name: str) -> Any:
    """Load a verbatim sandbox recording by file stem."""
    return json.loads((CAPTURED_DIR / f'{name}.json').read_text())


def load_wireless_synthetic(name: str) -> Any:
    """Load a synthetic access point payload by file stem."""
    return json.loads((WIRELESS_SYNTHETIC_DIR / f'{name}.json').read_text())


def metric_values(aggregator: Any, name: str, *required_tags: str) -> list[float]:
    """Values submitted for `name` on series carrying all of `required_tags`.

    `assert_metric(tags=...)` matches the whole tag set, which makes a test fail whenever an
    unrelated tag is added. This asserts on containment instead, so a test states only the tags
    it actually cares about.
    """
    return [metric.value for metric in aggregator.metrics(name) if all(t in metric.tags for t in required_tags)]


def with_value(payload: Any, dotted_path: str, value: Any) -> Any:
    """Return a deep copy of `payload` with `dotted_path` set to `value`.

    List indices are written as plain integers, so `response.0.metricsDetails.cpuScore`
    addresses the first record. The original payload is never modified.

    Raises:
        KeyError: if an intermediate key does not exist, so that a typo in a test fails loudly
            instead of silently creating a new field.
    """
    result = copy.deepcopy(payload)
    cursor = result
    parts = dotted_path.split('.')
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    leaf = parts[-1]
    if isinstance(cursor, list):
        cursor[int(leaf)] = value
    else:
        if leaf not in cursor:
            raise KeyError(f'{dotted_path!r} does not exist in the payload; check for a typo')
        cursor[leaf] = value
    return result


# -- HTTP fakes -----------------------------------------------------------------------

AUTH_PATH = '/dna/system/api/v1/auth/token'


class _Response:
    """Minimal stand-in for a `requests.Response`."""

    def __init__(self, payload: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {'x-correlation-id': 'test-correlation-id', **(headers or {})}

    def json(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


def _to_response(item: Any) -> _Response:
    """Build a response from a script entry.

    A plain value becomes a 200 with that value as the body. The `{'status_code': ...,
    'json': ...}` shape overrides both, so a script can also inject a failure. An exception is
    raised the way the transport would raise it, and an exception given as `json` is raised when
    the body is parsed.
    """
    if isinstance(item, BaseException):
        raise item
    if isinstance(item, dict) and 'status_code' in item and 'json' in item:
        return _Response(item['json'], item['status_code'], item.get('headers'))
    return _Response(item)


class ScriptedHttp:
    """Fake HTTP layer that replays a script and records what was asked of it.

    This is the only mock in the client tests. It sits exactly at the network boundary, so
    everything above it -- envelope unwrapping, pagination arithmetic, token lifecycle -- runs
    for real.
    """

    def __init__(self, script: list[Any], auth_script: list[Any] | None = None) -> None:
        self._script = list(script)
        #: Consumed before the unconditional success below, so a test can inject a throttled or
        #: failed authentication attempt without disturbing the token issued once it is exhausted.
        self._auth_script = list(auth_script) if auth_script else []
        self.requests: list[dict[str, Any]] = []
        self.auth_calls = 0

    #: Returned once the script is exhausted. A fake that replayed its last payload forever would
    #: make any collection whose size is an exact multiple of the page limit paginate endlessly --
    #: which is a defect in the fake, not in the client, since a real appliance answers the
    #: follow-up page with an empty list.
    EXHAUSTED: dict[str, Any] = {'response': [], 'version': '1.0'}

    #: The analytics endpoints are POST and answer with an object, not a list, and every slot in
    #: it is null rather than empty when there is no data. A single exhaustion payload cannot
    #: stand in for both shapes, so the fake mirrors the one the verb actually returns.
    EXHAUSTED_OBJECT: dict[str, Any] = {
        'response': {'attributes': None, 'aggregateAttributes': None, 'groups': None},
        'page': {'limit': 100, 'count': 0},
        'version': '1.0',
    }

    def _next(self, exhausted: Any = None) -> _Response:
        item = self._script.pop(0) if self._script else (exhausted or self.EXHAUSTED)
        return _to_response(item)

    def get(self, url: str, params: dict[str, Any] | None = None, **options: Any) -> _Response:
        self.requests.append({'url': url, 'params': params or {}, 'extra_headers': options.get('extra_headers', {})})
        return self._next()

    def post(self, url: str, **options: Any) -> _Response:
        if url.endswith(AUTH_PATH):
            if self._auth_script:
                return _to_response(self._auth_script.pop(0))
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
    """Serves a different payload depending on the `view` query parameter.

    The interfaces endpoint returns a different field set per view, so a collector that reads
    several views issues several calls. Routing on the parameter keeps the test honest about
    which call produced which fields.

    `by_path` routes on the request path instead, for collectors that also read a second
    endpoint. It is checked first, because that endpoint takes no `view` parameter and would
    otherwise fall through to the `None` view.

    Either mapping's values may also be the `{'status_code': ..., 'json': ...}` override shape
    `ScriptedHttp` uses, to inject a failure for one specific path or view without
    disturbing every other endpoint the same cycle touches.
    """

    def __init__(self, by_view: dict[str | None, Any], by_path: dict[str, Any] | None = None) -> None:
        super().__init__([])
        self._by_view = by_view
        self._by_path = by_path or {}

    def get(self, url: str, params: dict[str, Any] | None = None, **options: Any) -> _Response:
        params = params or {}
        self.requests.append({'url': url, 'params': params, 'extra_headers': options.get('extra_headers', {})})
        for path, payload in self._by_path.items():
            if url.endswith(path):
                return _to_response(payload)
        return _to_response(self._by_view[params.get('view')])


def client_from_payload(instance: InstanceType, payload: Any) -> CatalystCenterClient:
    """A client whose http layer answers every request with the same payload."""
    return CatalystCenterClient(instance, http=ScriptedHttp([payload]))


def client_from_script(instance: InstanceType, script: list[Any]) -> CatalystCenterClient:
    """A client whose http layer answers with each item in `script` in turn, repeating the last
    one once exhausted.
    """
    return CatalystCenterClient(instance, http=ScriptedHttp(script))
