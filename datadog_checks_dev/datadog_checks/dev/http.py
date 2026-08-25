# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Compatibility helpers for the base-owned backend-neutral HTTP fakes."""

import importlib
import json
import warnings
from collections.abc import Mapping
from datetime import timedelta
from http.client import responses as http_reasons
from textwrap import dedent
from typing import Any

from datadog_checks.base.stubs.http import (
    JSON_RESULT_UNSET,
    FakeHTTPClient,
    FakeHTTPResponse,
    RecordedRequest,
)
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError

__all__ = ['FakeHTTPClient', 'FakeHTTPResponse', 'MockHTTPResponse', 'RecordedRequest']


def MockHTTPResponse(
    content: str | bytes = '',
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    json_data: Any = None,
    file_path: str | None = None,
    cookies: Mapping[str, str] | None = None,
    elapsed_seconds: float = 0.1,
    normalize_content: bool = True,
    url: str = '',
    history: list[FakeHTTPResponse] | None = None,
) -> FakeHTTPResponse:
    """Build a base fake from the legacy pytest-fixture arguments.

    New tests should construct :class:`FakeHTTPResponse` directly and configure
    every result they consume.
    """
    response_headers = dict(headers or {})
    json_result = JSON_RESULT_UNSET

    if json_data is not None:
        json_result = json_data
        content = json.dumps(json_data)
        response_headers.setdefault('Content-Type', 'application/json')
    elif file_path is not None:
        with open(file_path, 'rb') as response_file:
            content = response_file.read()

    if normalize_content and (
        (isinstance(content, str) and content.startswith('\n'))
        or (isinstance(content, bytes) and content.startswith(b'\n'))
    ):
        content = dedent(content[1:]) if isinstance(content, str) else content[1:]

    content_bytes = content.encode('utf-8') if isinstance(content, str) else content
    text = content if isinstance(content, str) else content.decode('utf-8', errors='replace')

    if json_result is JSON_RESULT_UNSET and text:
        try:
            json_result = json.loads(text)
        except (TypeError, ValueError):
            pass

    status_error = None
    if status_code >= 400:
        error_kind = 'Client Error' if status_code < 500 else 'Server Error'
        status_error = HTTPClientStatusError(f'{status_code} {error_kind}')

    return FakeHTTPResponse(
        status_code=status_code,
        content=content_bytes,
        text=text,
        headers=response_headers,
        json_result=json_result,
        content_chunks=(content_bytes,) if content_bytes else (),
        lines=text.splitlines(),
        status_error=status_error,
        elapsed=timedelta(seconds=elapsed_seconds),
        cookies=cookies,
        url=url,
        history=history or (),
        reason=http_reasons.get(status_code, ''),
    )


def __getattr__(name: str) -> Any:
    if name == 'MockResponse':
        legacy = importlib.import_module('datadog_checks.dev.http_legacy').MockResponse
        warnings.warn(
            'datadog_checks.dev.http.MockResponse is deprecated and will be removed in a future release. '
            'Use FakeHTTPResponse from datadog_checks.base.stubs.http once your integration runs against '
            'a datadog-checks-base release that exposes it.',
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
