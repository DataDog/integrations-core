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
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import urlsplit

import requests
import requests_mock

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import (
    JSON_RESULT_UNSET,
    FakeHTTPResponse,
    RecordedRequest,
    RegisteredResponse,
    assert_has_recorded_request,
    assert_recorded_requests,
)
from datadog_checks.base.utils.http import RequestsWrapper, create_http_client, is_uds_url, quote_uds_url
from datadog_checks.base.utils.http_protocol import HTTPClient, HTTPHeaders


@dataclass(frozen=True, slots=True)
class SentRequest:
    """A request as it reached the wire, after the client applied its configuration."""

    method: str
    url: str
    headers: Mapping[str, str]


@dataclass
class _Registration:
    registered: RegisteredResponse
    served: int = 0


@dataclass
class _ActiveCall:
    """A client call in progress, and the fixture violations raised while serving it."""

    request: RecordedRequest
    violations: list[AssertionError] = field(default_factory=list)
    # The client resends a call only after an exception or an error status, never after a redirect, so a wire request
    # that follows a served redirect is that redirect being followed, even when its location is the call's own URL.
    redirected: bool = False

    def violation(self, message: str) -> AssertionError:
        error = AssertionError(message)
        self.violations.append(error)
        return error


class FakeHTTPFixture:
    """Registers responses for, and records the requests of, every check client created during a test."""

    def __init__(self) -> None:
        self.requests: list[RecordedRequest] = []
        self.sent: list[SentRequest] = []
        self._registrations: list[_Registration] = []
        # Checks may send requests from several threads. Choosing the first unserved registration and marking it
        # served must be atomic, or two concurrent requests could receive the same response while another goes unused.
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
        _check_servable(response)
        registered = RegisteredResponse(method, url, response, match_options or {})
        with self._lock:
            self._registrations.append(_Registration(registered))

    def assert_requests(self, expected: Iterable[RecordedRequest]) -> None:
        """Assert that the checks made exactly the expected calls, in order."""
        with self._lock:
            recorded = list(self.requests)
        assert_recorded_requests(recorded, expected)

    def assert_has_request(self, expected: RecordedRequest) -> None:
        """Assert that the checks made the expected call."""
        with self._lock:
            recorded = list(self.requests)
        assert_has_recorded_request(recorded, expected)

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
    def _record_call(self, method: str, url: str, options: Mapping[str, Any]) -> Iterator[list[AssertionError]]:
        """Record a client call, yielding the fixture violations its wire requests raise."""
        call = _ActiveCall(RecordedRequest(method=method, url=url, options=options))
        with self._lock:
            self.requests.append(call.request)
        # The wire request is served on the calling thread, from the innermost call it is making.
        stack = self._calls.__dict__.setdefault('stack', [])
        stack.append(call)
        try:
            yield call.violations
        finally:
            stack.pop()

    def _serve(self, wire_request: Any) -> requests.Response:
        """Answer one wire request on behalf of the client call that sent it."""
        stack = self._calls.__dict__.get('stack')
        if not stack:
            raise AssertionError(
                f'{wire_request.method} {wire_request.url} bypassed the check HTTP client. The fake_http fixture '
                'serves requests sent through clients from create_http_client() or fake_http.create_client().'
            )
        active = stack[-1]
        call = active.request
        with self._lock:
            self.sent.append(SentRequest(wire_request.method, wire_request.url, HTTPHeaders(wire_request.headers)))
            if active.redirected:
                raise active.violation(
                    f'{call.method} {call.url} followed a redirect to {wire_request.method} {wire_request.url}. The '
                    'fake_http fixture serves only the call itself; pass allow_redirects=False to receive a '
                    'registered redirect.'
                )
            if not _sends_call(wire_request, call):
                raise active.violation(
                    f'{call.method} {call.url} sent {wire_request.method} {wire_request.url}, for example by '
                    'fetching an auth token. The fake_http fixture serves only the call itself.'
                )
            matching = [r for r in self._registrations if r.registered.matches(call)]
            chosen = next((r for r in matching if not r.served), matching[-1] if matching else None)
            if chosen is None:
                raise active.violation(
                    f'No registered response matched {call.method} {call.url} with options {dict(call.options)!r}. '
                    f'Pending responses: {self._pending()!r}.'
                )
            chosen.served += 1
            outcome = chosen.registered.outcome
        if isinstance(outcome, Exception):
            raise outcome
        wire_response = _to_requests_response(wire_request, outcome)
        active.redirected = wire_response.is_redirect
        return wire_response


def _encode(value: bytes | str, encoding: str | None) -> bytes:
    return value if isinstance(value, bytes) else value.encode(encoding or 'utf-8')


def _sends_call(wire_request: Any, call: RecordedRequest) -> bool:
    """Whether the wire request is the call itself, possibly retried, rather than a nested request."""
    url = quote_uds_url(call.url) if is_uds_url(call.url) else call.url
    # The client normalizes the URL, for example its host case and path quoting, before sending it.
    prepared = requests.PreparedRequest()
    prepared.prepare_url(url, call.options.get('params'))
    expected, sent = urlsplit(prepared.url), urlsplit(wire_request.url)
    return wire_request.method == call.method and expected[:4] == sent[:4]


def _check_servable(response: object) -> None:
    if isinstance(response, Exception):
        return
    if not isinstance(response, FakeHTTPResponse):
        raise TypeError(f'The fake_http fixture serves FakeHTTPResponse objects or exceptions, not {response!r}.')
    lines = None if response._lines is None else _encoded_lines(response)
    body = _non_json_body(response)
    unsendable = {
        # These only exist on a response object, so the real client can't receive them from the wire.
        'elapsed': response.elapsed != timedelta(),
        'stream_error': response._stream_error is not None,
        'history': bool(response.history),
        'peer_cert': response._peer_cert is not None,
        'json_error': response._json_error is not None,
        'url': bool(response.url),
        # The body is streamed in chunks the client picks, not the configured ones.
        'content_chunks': len(response._content_chunks) > 1,
        # Lines are sent joined by newlines, so they must split back into the same lines.
        'lines': lines is not None and b'\n'.join(lines).splitlines() != lines,
    }
    # The wire carries one body, so the client derives every other view from it. Empty views are skipped because
    # FakeHTTPResponse derives `text` and `content_chunks` as empty when they are not given.
    conflicting = {
        # The client parses JSON from the body rather than returning json_result.
        'json_result': _json_contradicts_body(response),
        'content_chunks': body is not None
        and any(_encode(chunk, response.encoding) != body for chunk in response._content_chunks),
        # Text is compared decoded, because a binary body does not survive a decode and encode round trip.
        'text': body is not None
        and bool(response.text)
        and response.text != body.decode(response.encoding or 'utf-8', errors='replace'),
        'lines': bool(lines) and body is not None and body.splitlines() != lines,
    }
    if fields := [name for name, is_set in unsendable.items() if is_set]:
        raise ValueError(f'The fake_http fixture cannot send these FakeHTTPResponse fields on the wire: {fields}.')
    if fields := [name for name, is_set in conflicting.items() if is_set]:
        raise ValueError(
            f'These FakeHTTPResponse fields disagree with the body the fake_http fixture sends: {fields}. The client '
            'derives every view from one body, so set a single body field or make the others match it.'
        )


def _json_contradicts_body(response: FakeHTTPResponse) -> bool:
    body = _non_json_body(response)
    if response._json_result is JSON_RESULT_UNSET or body is None:
        return False
    try:
        return json.loads(body) != response._json_result
    except ValueError:
        return True


def _encoded_lines(response: FakeHTTPResponse) -> list[bytes]:
    return [_encode(line, response.encoding) for line in response._lines or ()]


def _non_json_body(response: FakeHTTPResponse) -> bytes | None:
    if response.content:
        return response.content
    if response._lines is not None:
        return b'\n'.join(_encoded_lines(response))
    if response._content_chunks:
        return b''.join(_encode(chunk, response.encoding) for chunk in response._content_chunks)
    if response.text:
        return _encode(response.text, response.encoding)
    return None


def _body(response: FakeHTTPResponse) -> bytes:
    body = _non_json_body(response)
    if body is None and response._json_result is not JSON_RESULT_UNSET:
        return _encode(json.dumps(response._json_result), response.encoding)
    return body or b''


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
def install(mocker: Any) -> Iterator[FakeHTTPFixture]:
    """Serve every request sent through check HTTP clients from a new `FakeHTTPFixture` until the context exits."""
    fake_http = FakeHTTPFixture()
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
        # Clients built outside AgentCheck.create_http_client, such as RequestsWrapper(...) or a client cached before
        # the fixture was installed, skip the check above, so check the client that sends each call.
        if not client._agnostic:
            raise AssertionError(
                f'{method.upper()} {url} was sent by a client that did not opt in to the backend-neutral contract. '
                'The fake_http fixture serves only opted-in clients: set AGNOSTIC_HTTP_CLIENT = True on the check, '
                'or pass agnostic=True to create_http_client().'
            )
        with fake_http._record_call(method, url, options) as violations:
            try:
                return send_request(client, method, url, options)
            finally:
                # The client may catch a violation, for example to renew its auth token and retry, so the call
                # fails with the first one even if it then succeeds.
                if violations:
                    raise violations[0]

    mocker.patch.object(AgentCheck, 'create_http_client', autospec=True, side_effect=create_opted_in_client)
    mocker.patch.object(RequestsWrapper, '_request', record_request)
    with requests_mock.Mocker() as wire:
        wire.add_matcher(fake_http._serve)
        yield fake_http
