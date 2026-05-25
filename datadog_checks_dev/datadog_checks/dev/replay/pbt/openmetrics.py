# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Small OpenMetrics helpers for replay-cache metamorphic tests.

This is intentionally not a complete OpenMetrics parser. It supports the simple
sample-line shapes emitted by many integration fixtures well enough to apply
safe metamorphic transformations, such as reordering labels, while preserving
unsupported lines unchanged so generators do not accidentally invent new input
semantics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

_SAMPLE_RE = re.compile(
    r'^(?P<name>[A-Za-z_:][A-Za-z0-9_:]*)'
    r'(?:\{(?P<labels>[^{}]*)\})?'
    r'\s+(?P<value>[^\s]+)'
    r'(?:\s+(?P<timestamp>[^\s]+))?'
    r'\s*$'
)
_LABEL_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


@dataclass(frozen=True)
class OpenMetricsSample:
    name: str
    labels: tuple[tuple[str, str], ...]
    value: str
    timestamp: str | None = None

    def semantic_key(self) -> tuple[str, tuple[tuple[str, str], ...], str, str | None]:
        return (self.name, tuple(sorted(self.labels)), self.value, self.timestamp)


def _split_label_parts(label_text: str) -> list[str] | None:
    if not label_text:
        return []

    parts: list[str] = []
    current: list[str] = []
    in_quotes = False
    escaped = False
    for char in label_text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == '\\':
            current.append(char)
            escaped = True
            continue
        if char == '"':
            current.append(char)
            in_quotes = not in_quotes
            continue
        if char == ',' and not in_quotes:
            parts.append(''.join(current).strip())
            current = []
            continue
        current.append(char)

    if in_quotes or escaped:
        return None

    parts.append(''.join(current).strip())
    return parts


def _unescape_label_value(value: str) -> str:
    return value.replace(r'\\', '\\').replace(r'\"', '"').replace(r'\n', '\n')


def _escape_label_value(value: str) -> str:
    return value.replace('\\', r'\\').replace('\n', r'\n').replace('"', r'\"')


def parse_sample_line(line: str) -> OpenMetricsSample | None:
    """Parse a simple OpenMetrics/Prometheus sample line.

    Comments, blank lines, unsupported syntax, and complex escaped labels return
    ``None`` so callers can preserve them unchanged.
    """
    if not line.strip() or line.lstrip().startswith('#'):
        return None

    match = _SAMPLE_RE.match(line)
    if not match:
        return None

    labels: list[tuple[str, str]] = []
    label_text = match.group('labels')
    if label_text is not None:
        parts = _split_label_parts(label_text)
        if parts is None:
            return None
        for part in parts:
            if not part:
                return None
            name, separator, raw_value = part.partition('=')
            if separator != '=' or not _LABEL_NAME_RE.match(name):
                return None
            if len(raw_value) < 2 or raw_value[0] != '"' or raw_value[-1] != '"':
                return None
            labels.append((name, _unescape_label_value(raw_value[1:-1])))

    return OpenMetricsSample(
        name=match.group('name'),
        labels=tuple(labels),
        value=match.group('value'),
        timestamp=match.group('timestamp'),
    )


def render_sample(sample: OpenMetricsSample, labels: Iterable[tuple[str, str]] | None = None) -> str:
    label_items = tuple(sample.labels if labels is None else labels)
    if label_items:
        label_text = ','.join(f'{name}="{_escape_label_value(value)}"' for name, value in label_items)
        prefix = f'{sample.name}{{{label_text}}}'
    else:
        prefix = sample.name

    if sample.timestamp is None:
        return f'{prefix} {sample.value}'
    return f'{prefix} {sample.value} {sample.timestamp}'


def reorder_sample_labels(line: str) -> str:
    """Return ``line`` with labels sorted by name/value, or unchanged if unsupported."""
    sample = parse_sample_line(line)
    if sample is None or len(sample.labels) < 2:
        return line
    return render_sample(sample, labels=sorted(sample.labels))


def mutate_body_label_order(body: str) -> str:
    return '\n'.join(reorder_sample_labels(line) for line in body.split('\n'))


def semantic_samples(body: str) -> list[tuple[str, tuple[tuple[str, str], ...], str, str | None]]:
    samples = []
    for line in body.split('\n'):
        sample = parse_sample_line(line)
        if sample is not None:
            samples.append(sample.semantic_key())
    return samples
