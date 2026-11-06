# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Compatibility re-exports for backend-neutral HTTP test fakes."""

import importlib
import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    # Runtime imports stay lazy so downstream suites can still use MockResponse with an older base release.
    from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest

    MockHTTPResponse = FakeHTTPResponse

__all__ = ['FakeHTTPClient', 'FakeHTTPResponse', 'MockHTTPResponse', 'RecordedRequest']

BASE_HTTP_REEXPORTS = {
    'FakeHTTPClient': 'FakeHTTPClient',
    'FakeHTTPResponse': 'FakeHTTPResponse',
    'MockHTTPResponse': 'FakeHTTPResponse',
    'RecordedRequest': 'RecordedRequest',
}


def __getattr__(name: str) -> Any:
    if target := BASE_HTTP_REEXPORTS.get(name):
        return getattr(importlib.import_module('datadog_checks.base.stubs.http'), target)

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
