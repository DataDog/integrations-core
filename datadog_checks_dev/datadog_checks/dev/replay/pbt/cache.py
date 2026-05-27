# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Helpers for building and mutating replay-cache directories in PBT.

These utilities operate on cached compare-check artifacts rather than live E2E
services. They let tests copy a seed replay cache, apply a semantics-preserving
mutation to adapter-captured data, and then feed that mutated cache back into
cached replay so failures are reproducible as ordinary artifact directories.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from datadog_checks.dev.replay.pbt.json import mutate_json_whitespace, mutate_object_key_order, mutate_string_escapes
from datadog_checks.dev.replay.pbt.openmetrics import (
    expand_sample_whitespace,
    insert_comment_and_blank_lines,
    mutate_body_label_order,
    mutate_help_text,
    remove_help_lines,
    toggle_final_newline,
    toggle_line_endings,
)


def copy_replay_cache(source: Path, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)
    return destination


def _request_capture_files(cache_dir: Path) -> list[Path]:
    manifest_path = cache_dir / 'capture.json'
    manifest = json.loads(manifest_path.read_text())
    if isinstance(manifest, dict):
        files = manifest.get('files', {})
        requests_file = files.get('requests') if isinstance(files, dict) else None
        if requests_file:
            return [cache_dir / str(requests_file)]
        return []
    if isinstance(manifest, list):
        return [manifest_path]
    return []


def _mutate_request_capture_bodies(
    cache_dir: Path,
    mutate_body: Callable[[str], str],
    should_mutate_record: Callable[[dict[str, Any]], bool] | None = None,
) -> int:
    changed_records = 0
    for capture_file in _request_capture_files(cache_dir):
        records: Any = json.loads(capture_file.read_text())
        if not isinstance(records, list):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue
            if should_mutate_record is not None and not should_mutate_record(record):
                continue
            body = record.get('body')
            if not isinstance(body, str):
                continue
            mutated_body = mutate_body(body)
            if mutated_body != body:
                record['body'] = mutated_body
                changed_records += 1

        capture_file.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    return changed_records


def mutate_request_capture_label_order(cache_dir: Path) -> int:
    """Sort labels in OpenMetrics response bodies for request replay captures.

    Returns the number of HTTP records whose body changed. Unsupported capture
    shapes or unsupported body lines are preserved unchanged.
    """
    return _mutate_request_capture_bodies(cache_dir, mutate_body_label_order)


def _is_not_strict_openmetrics_record(record: dict[str, Any]) -> bool:
    headers = record.get('headers')
    if not isinstance(headers, dict):
        return True
    for name, value in headers.items():
        if str(name).lower() != 'content-type':
            continue
        media_type = str(value).split(';', 1)[0].strip().lower()
        return media_type != 'application/openmetrics-text'
    return True


def mutate_request_capture_comments_and_blank_lines(cache_dir: Path) -> int:
    """Add semantically ignored comments and blank lines to Prometheus text request captures."""
    return _mutate_request_capture_bodies(
        cache_dir, insert_comment_and_blank_lines, should_mutate_record=_is_not_strict_openmetrics_record
    )


def mutate_request_capture_final_newline(cache_dir: Path) -> int:
    """Add or remove one final newline in Prometheus text request capture bodies."""
    return _mutate_request_capture_bodies(
        cache_dir, toggle_final_newline, should_mutate_record=_is_not_strict_openmetrics_record
    )


def mutate_request_capture_help_text(cache_dir: Path) -> int:
    """Replace HELP doc text in request capture bodies."""
    return _mutate_request_capture_bodies(cache_dir, mutate_help_text)


def mutate_request_capture_help_removal(cache_dir: Path) -> int:
    """Remove HELP lines from request capture bodies."""
    return _mutate_request_capture_bodies(cache_dir, remove_help_lines)


def _is_json_record(record: dict[str, Any]) -> bool:
    headers = record.get('headers')
    if isinstance(headers, dict):
        for name, value in headers.items():
            if str(name).lower() == 'content-type' and 'json' in str(value).lower():
                return True
    body = record.get('body')
    return isinstance(body, str) and body.lstrip()[:1] in {'{', '['}


def mutate_request_capture_json_object_key_order(cache_dir: Path) -> int:
    """Sort JSON object keys in request capture response bodies."""
    return _mutate_request_capture_bodies(cache_dir, mutate_object_key_order, should_mutate_record=_is_json_record)


def mutate_request_capture_json_whitespace(cache_dir: Path) -> int:
    """Change insignificant JSON whitespace in request capture response bodies."""
    return _mutate_request_capture_bodies(cache_dir, mutate_json_whitespace, should_mutate_record=_is_json_record)


def mutate_request_capture_json_string_escapes(cache_dir: Path) -> int:
    """Toggle JSON string escaping in request capture response bodies."""
    return _mutate_request_capture_bodies(cache_dir, mutate_string_escapes, should_mutate_record=_is_json_record)


def mutate_request_capture_line_endings(cache_dir: Path) -> int:
    """Convert between LF and CRLF line endings in OpenMetrics request capture bodies."""
    return _mutate_request_capture_bodies(
        cache_dir, toggle_line_endings, should_mutate_record=_is_not_strict_openmetrics_record
    )


def mutate_request_capture_sample_whitespace(cache_dir: Path) -> int:
    """Toggle whitespace separating sample name/labels from value in OpenMetrics bodies."""
    return _mutate_request_capture_bodies(
        cache_dir, expand_sample_whitespace, should_mutate_record=_is_not_strict_openmetrics_record
    )


def _flip_header_case(headers: dict[str, Any]) -> dict[str, Any] | None:
    if not headers:
        return None
    any_upper = any(any(char.isupper() for char in str(name)) for name in headers)
    new_headers: dict[str, Any] = {}
    changed = False
    for name, value in headers.items():
        original = str(name)
        flipped = original.lower() if any_upper else original.upper()
        if flipped != original:
            changed = True
        new_headers[flipped] = value
    if not changed or len(new_headers) != len(headers):
        return None
    return new_headers


def mutate_request_capture_header_casing(cache_dir: Path) -> int:
    """Flip the case of HTTP response header names in request capture records.

    HTTP/1.1 field names are case-insensitive (RFC 7230 §3.2), so a check that
    looks up captured response headers must not depend on the recorded casing.
    Returns the number of records whose headers changed. Records without a
    headers dictionary or whose header names are already all single-case are
    preserved unchanged.
    """
    changed_records = 0
    for capture_file in _request_capture_files(cache_dir):
        records: Any = json.loads(capture_file.read_text())
        if not isinstance(records, list):
            continue

        for record in records:
            if not isinstance(record, dict):
                continue
            headers = record.get('headers')
            if not isinstance(headers, dict):
                continue
            new_headers = _flip_header_case(headers)
            if new_headers is None:
                continue
            record['headers'] = new_headers
            changed_records += 1

        capture_file.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
    return changed_records
