# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Redaction helpers for genresources event payloads."""

from __future__ import annotations

import copy
import fnmatch
from collections.abc import Mapping, Sequence

REDACTED_PLACEHOLDER = "<redacted>"


def apply_deny_list(
    fields: Mapping[str, object],
    *,
    paths: Sequence[str],
    annotation_keys: Sequence[str],
) -> dict:
    """Return a deep copy of ``fields`` with deny-list matches replaced by ``"<redacted>"``.

    ``paths`` use dotted segments; ``[*]`` denotes "every element of the array
    at this segment." Paths that don't exist in the input are silently skipped.
    ``annotation_keys`` apply fnmatch globs to keys of ``metadata.annotations``.

    The input is never mutated. Failures during traversal do not raise — secrets
    must not leak because a deny-list path is malformed.
    """
    result = copy.deepcopy(dict(fields))

    for path in paths:
        _apply_path(result, path.split("."))

    metadata = result.get("metadata")
    annotations = metadata.get("annotations") if isinstance(metadata, dict) else None
    if isinstance(annotations, dict):
        for pattern in annotation_keys:
            for key in list(annotations.keys()):
                if fnmatch.fnmatchcase(key, pattern):
                    annotations[key] = REDACTED_PLACEHOLDER

    return result


def _apply_path(node: object, segments: list[str]) -> None:
    """Recursively redact the value at ``segments`` within ``node`` in-place."""
    if not segments:
        return
    head, *rest = segments

    if head.endswith("[*]"):
        head = head[:-3]
        if isinstance(node, Mapping) and head in node and isinstance(node[head], list):
            if not rest:
                for index in range(len(node[head])):
                    node[head][index] = REDACTED_PLACEHOLDER
                return
            for item in node[head]:
                _apply_path(item, rest)
        return

    if not rest:
        if isinstance(node, Mapping) and head in node:
            node[head] = REDACTED_PLACEHOLDER
        return

    if isinstance(node, Mapping) and head in node:
        _apply_path(node[head], rest)
