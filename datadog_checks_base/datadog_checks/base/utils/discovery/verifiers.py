# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Predicate factories for discovery probe verification.

Each public function returns a callable predicate. HTTP predicates take a
``requests.Response`` and return ``bool``. TCP predicates take ``bytes`` and
return ``bool``. The factory shape lets check classes declare verifiers as
class-level attributes, e.g. ``DISCOVERY_VERIFY = body_contains("Total Accesses:")``.
"""

import re
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests

_PROM_LINE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?(\s|$)")


HTTPPredicate = Callable[["requests.Response"], bool]
TCPPredicate = Callable[[bytes], bool]


def status_2xx() -> HTTPPredicate:
    def predicate(response: "requests.Response") -> bool:
        return 200 <= response.status_code < 300

    return predicate


def body_contains(needle: str) -> HTTPPredicate:
    def predicate(response: "requests.Response") -> bool:
        return 200 <= response.status_code < 300 and needle in response.text

    return predicate


def body_matches(pattern: str) -> HTTPPredicate:
    compiled = re.compile(pattern, re.MULTILINE)

    def predicate(response: "requests.Response") -> bool:
        if not (200 <= response.status_code < 300):
            return False
        return bool(compiled.search(response.text))

    return predicate


def json_has(required_keys: Iterable[str]) -> HTTPPredicate:
    keys = tuple(required_keys)

    def predicate(response: "requests.Response") -> bool:
        if not (200 <= response.status_code < 300):
            return False
        try:
            doc = response.json()
        except ValueError:
            return False
        if not isinstance(doc, dict):
            return False
        return all(k in doc for k in keys)

    return predicate


def is_prometheus_exposition() -> HTTPPredicate:
    """Verify a Prometheus / OpenMetrics exposition response.

    Status must be 2xx, Content-Type must be text/plain or
    application/openmetrics-text, and at least one non-comment line must look
    like a Prometheus metric line.
    """

    def predicate(response: "requests.Response") -> bool:
        if not (200 <= response.status_code < 300):
            return False
        ctype = response.headers.get("Content-Type", "").lower()
        if not (ctype.startswith("text/plain") or ctype.startswith("application/openmetrics-text")):
            return False
        for line in response.text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            return bool(_PROM_LINE.match(stripped))
        return False

    return predicate


def response_equals(expected: bytes) -> TCPPredicate:
    def predicate(buf: bytes) -> bool:
        return buf == expected

    return predicate


def response_starts_with(prefix: bytes) -> TCPPredicate:
    def predicate(buf: bytes) -> bool:
        return buf.startswith(prefix)

    return predicate
