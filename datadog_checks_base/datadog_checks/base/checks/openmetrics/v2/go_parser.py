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


def _json_to_metrics(family: dict, is_openmetrics: bool = False) -> Iterator[Metric]:
    """Convert a Go parser JSON family dict into one or more Metric objects.

    For Prometheus-format counters the Python ``prometheus_client`` parser
    only keeps samples whose name matches a recognised counter suffix
    (``_total``, ``_created``, or the bare family name) inside the counter
    family.  Non-standard suffixes (``_last``, ``_min``, ``_max``, ``_mean``,
    ``_stddev``, …) are emitted as separate ``unknown``-type families.

    The Go parser groups *all* samples between consecutive TYPE directives
    into one typed family, so we split them here to match the Python
    behaviour that downstream code relies on.
    """
    name = family['name']
    metric_type = family.get('type', 'untyped')
    raw_samples = family.get('samples', ())
    help_text = family.get('help', '')

    if not is_openmetrics and metric_type == 'counter':
        # --- split standard / non-standard counter samples ---------------
        standard_raw: list[dict] = []
        nonstandard_by_name: dict[str, list[dict]] = {}

        for s in raw_samples:
            sname = s['name']
            if sname == name or sname == name + '_total' or sname == name + '_created':
                standard_raw.append(s)
            else:
                nonstandard_by_name.setdefault(sname, []).append(s)

        # --- emit the counter family with standard samples only ----------
        if standard_raw:
            original_name = name
            if name.endswith('_total'):
                name = name[:-6]
            else:
                total_name = name + '_total'
                if any(s.get('name') == total_name for s in standard_raw):
                    name = total_name

            samples = []
            for s in standard_raw:
                sname = s['name']
                # Add _total to the bare-name sample (Python behaviour).
                if sname == original_name and not sname.endswith('_total'):
                    sname = sname + '_total'
                samples.append(Sample(
                    sname,
                    s.get('labels') or {},
                    _decode_value(s['value']),
                    s.get('timestamp'),
                    s.get('exemplar'),
                ))

            yield Metric(name, 'counter', help_text, samples)

        # --- emit unknown families for non-standard samples --------------
        for ns_name, ns_raw in nonstandard_by_name.items():
            yield Metric(
                ns_name,
                'unknown',
                '',
                [
                    Sample(
                        ns_name,
                        s.get('labels') or {},
                        _decode_value(s['value']),
                        s.get('timestamp'),
                        s.get('exemplar'),
                    )
                    for s in ns_raw
                ],
            )
    else:
        samples = [
            Sample(
                s['name'],
                s.get('labels') or {},
                _decode_value(s['value']),
                s.get('timestamp'),
                s.get('exemplar'),
            )
            for s in raw_samples
        ]
        yield Metric(name, metric_type, help_text, samples)


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
                    yield from _json_to_metrics(family, is_openmetrics=is_openmetrics)

        remaining_json = datadog_agent.finish_prometheus_parser(parser_id)
        if remaining_json:
            for family in json.loads(remaining_json):
                yield from _json_to_metrics(family, is_openmetrics=is_openmetrics)
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
