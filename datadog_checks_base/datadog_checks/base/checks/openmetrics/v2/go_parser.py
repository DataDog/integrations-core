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


def _json_to_metric(family: dict, is_openmetrics: bool = False) -> Metric:
    name = family['name']
    metric_type = family.get('type', 'untyped')
    raw_samples = family.get('samples', ())

    # The Python prometheus_client parser adds ``_total`` to the main counter
    # sample and strips it from the family name.  Non-standard suffixes
    # (``_last``, ``_min``, ``_max``, etc.) become separate "unknown" families.
    # The Go parser groups everything under one typed family.  Normalize here
    # so downstream code sees consistent names.
    original_name = name
    if not is_openmetrics and metric_type == 'counter':
        if name.endswith('_total'):
            name = name[:-6]
        else:
            total_name = name + '_total'
            if any(s.get('name') == total_name for s in raw_samples):
                name = total_name

    def _sample_name(raw_name):
        # Only add ``_total`` to the sample whose name matches the TYPE-line
        # family name exactly — that is the standard counter sample.
        # Non-standard samples (``_last``, ``_min``, etc.) are left as-is.
        if not is_openmetrics and metric_type == 'counter' and raw_name == original_name and not raw_name.endswith('_total'):
            return raw_name + '_total'
        return raw_name

    samples = [
        Sample(
            _sample_name(s['name']),
            s.get('labels') or {},
            _decode_value(s['value']),
            s.get('timestamp'),
            s.get('exemplar'),
        )
        for s in raw_samples
    ]

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
    media_type = content_type.split(';')[0] if content_type else ''
    is_openmetrics = media_type == 'application/openmetrics-text'

    parser_id = datadog_agent.new_prometheus_parser(content_type)
    try:
        for chunk in batched_lines(line_streamer, target_size=128):
            families_json = datadog_agent.feed_prometheus_parser(parser_id, chunk)
            if families_json:
                for family in json.loads(families_json):
                    yield _json_to_metric(family, is_openmetrics=is_openmetrics)

        remaining_json = datadog_agent.finish_prometheus_parser(parser_id)
        if remaining_json:
            for family in json.loads(remaining_json):
                yield _json_to_metric(family, is_openmetrics=is_openmetrics)
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
