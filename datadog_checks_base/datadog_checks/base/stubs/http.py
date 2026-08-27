# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Unpack

from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.base.utils.http_protocol import HTTPHeaders, HTTPRequestOptions, HTTPResponse

__all__ = ['FakeHTTPClient', 'FakeHTTPResponse', 'RecordedRequest']

JSON_RESULT_UNSET = object()
SUPPRESSED_AUTH = object()


@dataclass(frozen=True, slots=True)
class RecordedRequest:
    """A request captured by :class:`FakeHTTPClient`."""

    method: str
    url: str
    options: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'method', self.method.upper())
        object.__setattr__(self, 'options', MappingProxyType(dict(self.options)))


@dataclass(frozen=True, slots=True)
class RegisteredResponse:
    method: str
    url: str
    outcome: HTTPResponse | Exception
    match_options: Mapping[str, Any]


class FakeHTTPResponse:
    """Backend-neutral response whose outcomes are configured directly by tests."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b'',
        text: str = '',
        headers: Mapping[str, str] | None = None,
        json_result: Any = JSON_RESULT_UNSET,
        json_error: Exception | None = None,
        content_chunks: Iterable[bytes | str] = (),
        lines: Iterable[bytes | str] = (),
        status_error: HTTPClientStatusError | None = None,
        encoding: str | None = None,
        elapsed: timedelta = timedelta(),
        cookies: Mapping[str, str] | None = None,
        links: Mapping[str, Mapping[str, str]] | None = None,
        url: str = '',
        history: Iterable[HTTPResponse] = (),
        reason: str = '',
        peer_cert: bytes | dict | None = None,
    ) -> None:
        self.status_code: int = status_code
        self.content: bytes = content
        self.text: str = text
        self.headers: Mapping[str, str] = HTTPHeaders(headers or {})
        self.encoding: str | None = encoding
        self.elapsed: timedelta = elapsed
        self.cookies: Mapping[str, str] = MappingProxyType(dict(cookies or {}))
        self.links: Mapping[str, Mapping[str, str]] = MappingProxyType(
            {name: MappingProxyType(dict(link)) for name, link in (links or {}).items()}
        )
        self.url: str = url
        self.history: list[HTTPResponse] = list(history)
        self.closed = False
        self._json_result = json_result
        self._json_error = json_error
        self._content_chunks = tuple(content_chunks)
        self._lines = tuple(lines)
        self._status_error = status_error
        self._reason = reason
        self._peer_cert = peer_cert

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    @property
    def reason(self) -> str:
        return self._reason

    def json(self, **kwargs: Any) -> Any:
        if self._json_error is not None:
            raise self._json_error
        if self._json_result is JSON_RESULT_UNSET:
            raise ValueError('No JSON result was configured for this fake response.')
        return self._json_result

    def raise_for_status(self) -> None:
        if self._status_error is None:
            return
        if self._status_error.response is None:
            self._status_error.response = self
        raise self._status_error

    def close(self) -> None:
        self.closed = True

    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None:
        return self._peer_cert

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        yield from self._content_chunks

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        yield from self._lines

    def __enter__(self) -> HTTPResponse:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None

    def __iter__(self) -> Iterator[bytes | str]:
        return self.iter_content()

    def __bool__(self) -> bool:
        return self.ok


class FakeHTTPClient:
    """Backend-neutral HTTP client fake with explicit response registration."""

    def __init__(
        self,
        *,
        options: Mapping[str, Any] | None = None,
        tls_config: Mapping[str, Any] | None = None,
        cookies: Mapping[str, str] | None = None,
        should_bypass_proxy: bool = False,
    ) -> None:
        self.options: dict[str, Any] = {
            'auth': None,
            'cert': None,
            'headers': {},
            'proxies': None,
            'timeout': (10.0, 10.0),
            'verify': True,
            'allow_redirects': True,
        }
        if options is not None:
            self.options.update(options)
        self.options['headers'] = dict(self.options.get('headers') or {})
        self.tls_config = dict(tls_config or {})
        self.trust_env = True
        self.ignore_tls_warning = False
        self.persist_connections = False
        self.requests: list[RecordedRequest] = []
        self.closed = False
        self._cookies = dict(cookies or {})
        self._should_bypass_proxy = should_bypass_proxy
        self._responses: list[RegisteredResponse] = []

    def register_response(
        self,
        method: str,
        url: str,
        response: HTTPResponse | Exception,
        *,
        match_options: Mapping[str, Any] | None = None,
    ) -> None:
        """Queue a response or exception for the first matching request."""
        self._responses.append(
            RegisteredResponse(
                method=method.upper(),
                url=url,
                outcome=response,
                match_options=MappingProxyType(dict(match_options or {})),
            )
        )

    def get(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('GET', url, options)

    def post(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('POST', url, options)

    def head(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('HEAD', url, options)

    def put(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('PUT', url, options)

    def patch(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('PATCH', url, options)

    def delete(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('DELETE', url, options)

    def options_method(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        return self._request('OPTIONS', url, options)

    def get_header(self, name: str, default: str | None = None) -> str | None:
        found = default
        for header_name, value in self.options['headers'].items():
            if header_name.lower() == name.lower():
                found = value
        return found

    def set_header(self, name: str, value: str) -> None:
        matching_names = [header_name for header_name in self.options['headers'] if header_name.lower() == name.lower()]
        if not matching_names:
            self.options['headers'][name] = value
            return

        retained_name = matching_names[0]
        self.options['headers'][retained_name] = value
        for duplicate_name in matching_names[1:]:
            del self.options['headers'][duplicate_name]

    def disable_auth(self) -> None:
        self.options['auth'] = SUPPRESSED_AUTH

    def close(self) -> None:
        self.closed = True

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        return self._cookies.get(name, default)

    def should_bypass_proxy(self, url: str) -> bool:
        return self._should_bypass_proxy

    def assert_requests(self, expected: Iterable[RecordedRequest]) -> None:
        expected_requests = list(expected)
        if self.requests != expected_requests:
            raise AssertionError(f'Expected recorded requests {expected_requests!r}, got {self.requests!r}.')

    def assert_has_request(self, expected: RecordedRequest) -> None:
        if expected not in self.requests:
            raise AssertionError(f'No recorded request matched {expected!r}. Recorded requests: {self.requests!r}.')

    def assert_all_responses_consumed(self) -> None:
        count = len(self._responses)
        if count:
            noun = 'response was' if count == 1 else 'responses were'
            raise AssertionError(f'{count} registered {noun} not consumed: {self._responses!r}.')

    def _request(self, method: str, url: str, options: Mapping[str, Any]) -> HTTPResponse:
        request = RecordedRequest(method=method, url=url, options=options)
        self.requests.append(request)

        for index, registered in enumerate(self._responses):
            if self._matches(registered, request):
                outcome = self._responses.pop(index).outcome
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome

        raise AssertionError(
            f'No registered response matched {request.method} {request.url} with options {dict(request.options)!r}. '
            f'Pending responses: {self._responses!r}.'
        )

    @staticmethod
    def _matches(registered: RegisteredResponse, request: RecordedRequest) -> bool:
        return (
            registered.method == request.method
            and registered.url == request.url
            and all(
                request.options.get(name, JSON_RESULT_UNSET) == value
                for name, value in registered.match_options.items()
            )
        )


if TYPE_CHECKING:
    from datadog_checks.base.utils.http_protocol import HTTPClient

    client: HTTPClient = FakeHTTPClient()
    response: HTTPResponse = FakeHTTPResponse()
