# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Back the `fake_http` fixture with requests-mock, so checks run their real HTTP client.

Calls are recorded and matched where checks call their client, so `RecordedRequest` and `match_options` keep their
`FakeHTTPClient` meaning, and requests-mock serves the matched response. This lives in dev because base ships with
the Agent and must not import requests-mock.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import requests
import requests_mock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import (
    JSON_RESULT_UNSET,
    FakeHTTPClient,
    FakeHTTPResponse,
    RecordedRequest,
    RegisteredResponse,
    _snapshot_options,
)
from datadog_checks.base.utils.http import RequestsWrapper, create_http_client
from datadog_checks.base.utils.http_protocol import HTTPClient


@dataclass
class _Registration:
    registered: RegisteredResponse
    served: int = 0


class FakeHTTP:
    """Registers responses for, and records the requests of, every check client created during a test."""

    assert_requests = FakeHTTPClient.assert_requests
    assert_has_request = FakeHTTPClient.assert_has_request

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self._registrations: list[_Registration] = []
        # Concurrent requests must not both claim, or skip, the same pending registration.
        self._lock = threading.Lock()
        self._calls = threading.local()

    def create_client(self) -> HTTPClient:
        """Create a client with default configuration whose requests this fixture serves."""
        return create_http_client({}, {}, agnostic=True)

    def register_response(
        self,
        method: str,
        url: str,
        response: FakeHTTPResponse | Exception,
        *,
        match_options: Mapping[str, Any] | None = None,
    ) -> None:
        """Serve a response or raise an exception for matching requests.

        Registrations matching the same request are served in order, and the last one then repeats.
        """
        registered = RegisteredResponse(
            method=method.upper(), url=url, outcome=response, match_options=_snapshot_options(match_options or {})
        )
        with self._lock:
            self._registrations.append(_Registration(registered))

    def assert_all_responses_consumed(self) -> None:
        """Assert that every registration was served at least once."""
        with self._lock:
            pending = self._pending()
        if pending:
            noun = 'response was' if len(pending) == 1 else 'responses were'
            raise AssertionError(f'{len(pending)} registered {noun} not consumed: {pending!r}.')

    def _pending(self) -> list[RegisteredResponse]:
        return [registration.registered for registration in self._registrations if not registration.served]

    @contextmanager
    def _record_call(self, method: str, url: str, options: Mapping[str, Any]) -> Iterator[None]:
        request = RecordedRequest(method=method, url=url, options=options)
        with self._lock:
            self.requests.append(request)
        # The wire request is served on the calling thread, from the innermost call it is making.
        stack = self._calls.__dict__.setdefault('stack', [])
        stack.append(request)
        try:
            yield
        finally:
            stack.pop()

    def _serve(self, wire_request: Any) -> requests.Response | None:
        stack = self._calls.__dict__.get('stack')
        if not stack:
            # Not sent through a check client; requests-mock raises NoMockAddress.
            return None
        call = stack[-1]
        with self._lock:
            matching = [r for r in self._registrations if FakeHTTPClient._matches(r.registered, call)]
            chosen = next((r for r in matching if not r.served), matching[-1] if matching else None)
            if chosen is None:
                raise AssertionError(
                    f'No registered response matched {call.method} {call.url} with options {dict(call.options)!r}. '
                    f'Pending responses: {self._pending()!r}.'
                )
            chosen.served += 1
            outcome = chosen.registered.outcome
        if isinstance(outcome, Exception):
            raise outcome
        return _to_requests_response(wire_request, outcome)


def _encode(value: bytes | str, encoding: str | None) -> bytes:
    return value if isinstance(value, bytes) else value.encode(encoding or 'utf-8')


def _body(response: FakeHTTPResponse) -> bytes:
    if response.content:
        return response.content
    if response._lines is not None:
        return b'\n'.join(_encode(line, response.encoding) for line in response._lines)
    if response._content_chunks:
        return b''.join(_encode(chunk, response.encoding) for chunk in response._content_chunks)
    if response.text:
        return _encode(response.text, response.encoding)
    if response._json_result is not JSON_RESULT_UNSET:
        return _encode(json.dumps(response._json_result), response.encoding)
    return b''


def _to_requests_response(wire_request: Any, response: FakeHTTPResponse) -> requests.Response:
    headers = dict(response.headers)
    if response.links:
        headers['Link'] = ', '.join(
            f'<{link["url"]}>; ' + '; '.join(f'{k}="{v}"' for k, v in {'rel': rel, **link}.items() if k != 'url')
            for rel, link in response.links.items()
        )
    wire_response = requests_mock.create_response(
        wire_request,
        status_code=response.status_code,
        content=_body(response),
        headers=headers,
        reason=response.reason or None,
        cookies=dict(response.cookies) or None,
    )
    if response.encoding is not None:
        wire_response.encoding = response.encoding
    return wire_response


@contextmanager
def install(mocker: Any) -> Iterator[FakeHTTP]:
    """Serve every request sent through check HTTP clients from a new `FakeHTTP` until the context exits."""
    fake_http = FakeHTTP()
    create_check_client = AgentCheck.create_http_client
    send_request = RequestsWrapper._request

    def create_opted_in_client(check: AgentCheck, *args: Any, **kwargs: Any) -> HTTPClient:
        # The fixture models the backend-neutral contract, which a check only gets in production by opting in.
        if not getattr(check, 'AGNOSTIC_HTTP_CLIENT', False):
            raise AssertionError(
                f'{type(check).__name__} must set AGNOSTIC_HTTP_CLIENT = True to use the fake_http fixture.'
            )
        return create_check_client(check, *args, **kwargs)

    def record_request(client: RequestsWrapper, method: str, url: str, options: dict[str, Any]) -> Any:
        with fake_http._record_call(method, url, options):
            return send_request(client, method, url, options)

    mocker.patch.object(AgentCheck, 'create_http_client', autospec=True, side_effect=create_opted_in_client)
    mocker.patch.object(RequestsWrapper, '_request', record_request)
    with requests_mock.Mocker() as wire:
        wire.add_matcher(fake_http._serve)
        yield fake_http
