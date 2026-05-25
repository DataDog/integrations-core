# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Best-effort secret redaction for replay artifacts.

Replay fixtures are meant to be portable test inputs, so they should not retain
credential material from check configs, requests, subprocess output, or emitted
metric tags. The helpers here intentionally prefer deterministic replacement
values over deletion so replay matching can still work when both config and
captured records are scrubbed the same way.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = '<REDACTED>'

SENSITIVE_KEY_RE = re.compile(
    r'(?i)(^|[_\-.])(authorization|proxy-authorization|cookie|set-cookie|api[_-]?key|app[_-]?key|application[_-]?key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|secret|password|passwd|passphrase|private[_-]?key|client[_-]?secret|credential|signature|csrf|xsrf|access[_-]?key|secret[_-]?key)($|[_\-.])'
)
SENSITIVE_QUERY_KEY_RE = re.compile(
    r'(?i)(api[_-]?key|app[_-]?key|application[_-]?key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|secret|password|passwd|passphrase|client[_-]?secret|signature|credential|csrf|xsrf)'
)
SENSITIVE_TAG_KEY_RE = re.compile(
    r'(?i)(api[_-]?key|app[_-]?key|application[_-]?key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|secret|password|passwd|passphrase|client[_-]?secret|credential)'
)
SENSITIVE_SESSION_KEY_RE = re.compile(r'(?i)(^|[_\-.])session(?:$|[_\-.]?id($|[_\-.]))')

KEY_VALUE_TEXT_RE = re.compile(
    r'(?i)\b(api[_-]?key|app[_-]?key|application[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|token|secret|password|passwd|client[_-]?secret|signature|session)=("[^"\n]*"|[^&\s,}]+)'
)

TEXT_REPLACEMENTS = (
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]{8,}={0,2}'),
    re.compile(r'(?i)\bBasic\s+[A-Za-z0-9+/]{12,}={0,2}'),
    re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'),
    re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----', re.DOTALL),
)


def is_sensitive_key(key: str) -> bool:
    return bool(SENSITIVE_KEY_RE.search(key) or SENSITIVE_SESSION_KEY_RE.search(key))


def is_sensitive_query_key(key: str) -> bool:
    return bool(SENSITIVE_QUERY_KEY_RE.search(key) or SENSITIVE_SESSION_KEY_RE.search(key))


def is_sensitive_tag_key(key: str) -> bool:
    return bool(SENSITIVE_TAG_KEY_RE.search(key) or SENSITIVE_SESSION_KEY_RE.search(key))


def redact_key_value_match(match: re.Match[str]) -> str:
    key = match.group(1)
    value = match.group(2)
    if value.startswith('"') and value.endswith('"'):
        return f'{key}="{REDACTED}"'
    return f'{key}={REDACTED}'


def scrub_text(value: str) -> str:
    scrubbed = KEY_VALUE_TEXT_RE.sub(redact_key_value_match, value)
    for pattern in TEXT_REPLACEMENTS:
        scrubbed = pattern.sub(REDACTED, scrubbed)
    return scrubbed


def scrub_url(url: str) -> str:
    try:
        parts = urlsplit(url)
    except Exception:
        return scrub_text(url)

    query = []
    changed = False
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if is_sensitive_query_key(key):
            query.append((key, REDACTED))
            changed = True
        else:
            query.append((key, scrub_text(value)))
    if not changed and not parts.query:
        return scrub_text(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


def scrub_tag(tag: str) -> str:
    key, sep, value = tag.partition(':')
    if sep and is_sensitive_tag_key(key):
        return f'{key}:{REDACTED}'
    return scrub_text(tag)


def scrub_json(value: Any, *, key: str | None = None) -> Any:
    if key is not None and is_sensitive_key(str(key)):
        return REDACTED

    if isinstance(value, dict):
        return {str(child_key): scrub_json(child_value, key=str(child_key)) for child_key, child_value in value.items()}

    if isinstance(value, list):
        return [scrub_json(item) for item in value]

    if isinstance(value, tuple):
        return [scrub_json(item) for item in value]

    if isinstance(value, str):
        return scrub_text(value)

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    return scrub_text(str(value))


def scrub_output(value: Any) -> Any:
    """Scrub normalized/raw check output while preserving metric structure."""
    if isinstance(value, dict):
        scrubbed = {}
        for key, child in value.items():
            if key == 'tags' and isinstance(child, list):
                scrubbed[key] = [scrub_tag(str(tag)) for tag in child]
            else:
                scrubbed[key] = scrub_output(child)
        return scrubbed
    if isinstance(value, list):
        return [scrub_output(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value


def scrub_request_record(record: dict[str, Any]) -> dict[str, Any]:
    scrubbed = dict(record)
    if isinstance(scrubbed.get('method'), str):
        scrubbed['method'] = scrubbed['method'].upper()
    if isinstance(scrubbed.get('url'), str):
        scrubbed['url'] = scrub_url(scrubbed['url'])
    if isinstance(scrubbed.get('headers'), dict):
        scrubbed['headers'] = scrub_json(scrubbed['headers'])
    if isinstance(scrubbed.get('request_headers'), dict):
        scrubbed['request_headers'] = scrub_json(scrubbed['request_headers'])
    if 'request_json' in scrubbed:
        scrubbed['request_json'] = scrub_json(scrubbed['request_json'])
    if isinstance(scrubbed.get('request_data'), str):
        scrubbed['request_data'] = scrub_text(scrubbed['request_data'])
    else:
        scrubbed['request_data'] = scrub_json(scrubbed.get('request_data')) if 'request_data' in scrubbed else None
        if scrubbed.get('request_data') is None:
            scrubbed.pop('request_data', None)
    body = scrubbed.get('body')
    if isinstance(body, str):
        content_type = ''
        headers = scrubbed.get('headers')
        if isinstance(headers, dict):
            content_type = str(headers.get('Content-Type') or headers.get('content-type') or '')
        if 'json' in content_type.lower():
            try:
                scrubbed['body'] = json.dumps(scrub_json(json.loads(body)), sort_keys=True)
            except Exception:
                scrubbed['body'] = scrub_text(body)
        else:
            scrubbed['body'] = scrub_text(body)
    return scrubbed
