# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import List, Sequence, TypedDict, cast

from datadog_checks.base import ConfigurationError

from ..models import OID
from ..resolver import OIDResolver
from .extractor import MetricExtractor
from .models import ParsedMetric, ParsedSymbolMetric
from .table_metrics import parse_table_metric
from .types import Metric, MIBMetric, OIDMetric, SymbolMetric, TableMetric

MetricsParseResult = TypedDict(
    'MetricsParseResult', {'all_oids': List[OID], 'bulk_oids': List[OID], 'parsed_metrics': List[ParsedMetric]},
)


def parse_metrics(metrics, resolver, bulk_threshold=0):
    # type: (List[Metric], OIDResolver, int) -> MetricsParseResult
    all_oids = []  # type: List[OID]
    bulk_oids = []  # type: List[OID]

    extractor = MetricExtractor(resolver)

    parsed_metrics = []  # type: List[ParsedMetric]
    for metric in metrics:
        parsed_metrics.extend(_parse_metric(extractor, metric))

    for oid, batch in extractor.iter_oid_batches():
        if not batch:
            all_oids.append(oid)
        elif bulk_threshold and len(batch) > bulk_threshold:
            bulk_oids.append(oid)
        else:
            # Batch is too small to be queried in bulk.
            all_oids.extend(batch)

    return {
        'all_oids': all_oids,
        'bulk_oids': bulk_oids,
        'parsed_metrics': parsed_metrics,
    }


# Helpers.


def _parse_metric(extractor, metric):
    # type: (MetricExtractor, Metric) -> Sequence[ParsedMetric]
    if 'MIB' in metric:
        metric = cast(MIBMetric, metric)
        return _parse_mib_metric(extractor, metric)

    if 'OID' in metric:
        metric = cast(OIDMetric, metric)
        return [_parse_oid_metric(extractor, metric)]

    raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))


def _parse_mib_metric(extractor, metric):
    # type: (MetricExtractor, MIBMetric) -> Sequence[ParsedMetric]
    if 'symbol' in metric:
        metric = cast(SymbolMetric, metric)
        return [_parse_symbol_mib_metric(extractor, metric)]
    elif 'table' in metric:
        metric = cast(TableMetric, metric)
        return parse_table_metric(extractor, metric)
    else:
        raise ConfigurationError('When specifying a MIB, you must specify either table or symbol')


def _parse_symbol_mib_metric(extractor, metric):
    # type: (MetricExtractor, SymbolMetric) -> ParsedSymbolMetric
    mib = metric['MIB']
    symbol = metric['symbol']

    parsed_metric_name = extractor.extract_mib_symbol(mib, symbol)

    return ParsedSymbolMetric(
        name=parsed_metric_name, tags=metric.get('metric_tags', []), forced_type=metric.get('forced_type')
    )


def _parse_oid_metric(extractor, metric):
    # type: (MetricExtractor, OIDMetric) -> ParsedSymbolMetric
    extractor.add(metric['OID'], name=metric['name'])

    return ParsedSymbolMetric(
        name=metric['name'],
        tags=metric.get('metric_tags', []),
        forced_type=metric.get('forced_type'),
        enforce_scalar=False,
    )
