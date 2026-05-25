# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Semantics-preserving JSON body mutations for replay PBT."""

from __future__ import annotations

import json
from typing import Any


def parse_json_body(body: str) -> Any:
    return json.loads(body)


def semantic_json(body: str) -> Any | None:
    try:
        return parse_json_body(body)
    except Exception:
        return None


def mutate_object_key_order(body: str) -> str:
    """Recursively sort object keys while preserving decoded JSON values."""
    try:
        value = parse_json_body(body)
    except Exception:
        return body

    mutated = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return mutated if json.loads(mutated) == value else body


def mutate_json_whitespace(body: str) -> str:
    """Reserialize JSON with insignificant whitespace changes."""
    try:
        value = parse_json_body(body)
    except Exception:
        return body

    compact = json.dumps(value, sort_keys=False, separators=(',', ':'), ensure_ascii=False)
    pretty = json.dumps(value, sort_keys=False, indent=2, ensure_ascii=False)
    mutated = pretty if body == compact else compact
    return mutated if json.loads(mutated) == value else body


def mutate_string_escapes(body: str) -> str:
    """Toggle JSON string escaping without changing decoded values."""
    try:
        value = parse_json_body(body)
    except Exception:
        return body

    ascii_body = json.dumps(value, sort_keys=False, separators=(',', ':'), ensure_ascii=True)
    unicode_body = json.dumps(value, sort_keys=False, separators=(',', ':'), ensure_ascii=False)
    mutated = unicode_body if body == ascii_body else ascii_body
    return mutated if json.loads(mutated) == value else body
