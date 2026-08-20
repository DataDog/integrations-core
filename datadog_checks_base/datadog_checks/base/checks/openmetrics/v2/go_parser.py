# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import logging
from itertools import islice
from typing import TYPE_CHECKING

from datadog_checks.base.agent import datadog_agent

if TYPE_CHECKING:
    from collections.abc import Iterator

log = logging.getLogger(__name__)


class Sample:
    """Drop-in replacement for prometheus_client.samples.Sample.

    Attributes are mutable so that downstream code (label normalization,
    histogram decumulation, code-class injection) can modify labels in place.
    Constructable with positional args ``(name, labels, value)`` for
    compatibility with ``decumulate_histogram_buckets``.
    """

    __slots__ = ('name', 'labels', 'value', 'timestamp', 'exemplar')

    def __init__(
        self,
        name: str,
        labels: dict[str, str],
        value: float,
        timestamp: float | None = None,
        exemplar: object | None = None,
    ):
        self.name = name
        self.labels = labels
        self.value = value
        self.timestamp = timestamp
        self.exemplar = exemplar

    def __repr__(self):
        return f"Sample(name={self.name!r}, labels={self.labels!r}, value={self.value!r})"


class Metric:
    """Drop-in replacement for prometheus_client.metrics_core.Metric.

    Only the attributes consumed by the V2 pipeline are provided.
    """

    __slots__ = ('name', 'type', 'documentation', 'samples')

    def __init__(self, name: str, type: str, documentation: str, samples: list[Sample]):
        self.name = name
        self.type = type
        self.documentation = documentation
        self.samples = samples

    def __repr__(self):
        return f"Metric(name={self.name!r}, type={self.type!r}, samples={len(self.samples)})"


def batched_lines(line_iter: Iterator[str], target_size: int = 128) -> Iterator[str]:
    """Yield batches of lines joined with newlines.

    Each batch contains up to ``target_size`` lines, joined into a single
    string.  This amortizes CGo call overhead when feeding the Go parser.
    """
    while True:
        batch = list(islice(line_iter, target_size))
        if not batch:
            break
        yield '\n'.join(batch)


_NAN_INF_MAP = {'NaN': float('nan'), '+Inf': float('inf'), '-Inf': float('-inf')}


def _decode_value(v: float | str) -> float:
    """Decode a sample value from the Go parser.

    The Go parser encodes NaN and ±Inf as JSON strings to work around
    encoding/json's rejection of non-finite floats.
    """
    if isinstance(v, str):
        return _NAN_INF_MAP[v]
    return v


def _json_to_metric(family: dict) -> Metric:
    samples = [
        Sample(
            s['name'],
            s.get('labels') or {},
            _decode_value(s['value']),
            s.get('timestamp'),
            s.get('exemplar'),
        )
        for s in family.get('samples', ())
    ]
    name = family['name']
    metric_type = family.get('type', 'untyped')
    # The Python prometheus_client text parser strips the `_total` suffix from
    # counter metric family names (e.g. `foo_total` → family name `foo`).
    # Mirror that behaviour here so existing metric maps that key on the
    # suffix-free name continue to match when the Go parser is active.
    if metric_type == 'counter' and name.endswith('_total'):
        name = name[:-6]
    return Metric(
        name,
        metric_type,
        family.get('help', ''),
        samples,
    )


def parse_with_go_parser(content_type: str, line_streamer: Iterator[str]) -> Iterator[Metric]:
    """Parse prometheus/openmetrics text using the Go parser exposed via ``datadog_agent``.

    This is a drop-in replacement for ``text_fd_to_metric_families`` that
    delegates the actual text parsing to Go for better performance while
    preserving the Python streaming pipeline's memory characteristics.

    The Go parser is stateful: ``new_prometheus_parser`` creates a parser
    handle, ``feed_prometheus_parser`` sends a batch of lines and returns
    any complete metric families parsed so far, and ``finish_prometheus_parser``
    flushes remaining data and releases the handle.
    """
    parser_id = datadog_agent.new_prometheus_parser(content_type)
    try:
        for chunk in batched_lines(line_streamer, target_size=128):
            families_json = datadog_agent.feed_prometheus_parser(parser_id, chunk)
            if families_json:
                for family in json.loads(families_json):
                    yield _json_to_metric(family)

        remaining_json = datadog_agent.finish_prometheus_parser(parser_id)
        if remaining_json:
            for family in json.loads(remaining_json):
                yield _json_to_metric(family)
    except GeneratorExit:
        # Generator was closed before finishing; clean up the Go-side parser.
        try:
            datadog_agent.finish_prometheus_parser(parser_id)
        except Exception:
            pass
    except Exception:
        try:
            datadog_agent.finish_prometheus_parser(parser_id)
        except Exception:
            pass
        raise
