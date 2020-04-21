# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import List, TypedDict, cast

from datadog_checks.base import ConfigurationError

from ...models import OID
from ...resolver import OIDResolver
from ..parsed_metrics import ParsedMetric
from .models import ParseResult
from .oid_metrics import parse_oid_metric
from .symbol_metrics import parse_symbol_metric
from .table_metrics import parse_table_metric
from .types import Metric, OIDMetric, SymbolMetric, TableMetric

MetricsParseResult = TypedDict(
    'MetricsParseResult', {'all_oids': List[OID], 'bulk_oids': List[OID], 'parsed_metrics': List[ParsedMetric]},
)


def parse_metrics(metrics, resolver, bulk_threshold=0):
    # type: (List[Metric], OIDResolver, int) -> MetricsParseResult
    """
    Parse the `metrics` section of a config file, and return OIDs to fetch and metrics to submit.
    """
    all_oids = []
    bulk_oids = []
    parsed_metrics = []  # type: List[ParsedMetric]

    for metric in metrics:
        result = parse_metric(metric)

        for name, oid in result.oids_to_resolve.items():
            resolver.register(oid.as_tuple(), name)

        for oid in result.oids_to_fetch:
            all_oids.append(oid)

        for index_mapping in result.index_mappings:
            resolver.register_index(tag=index_mapping.tag, index=index_mapping.index, mapping=index_mapping.mapping)

        for batch in result.table_batches.values():
            should_query_in_bulk = bulk_threshold and len(batch.oids) > bulk_threshold
            if should_query_in_bulk:
                bulk_oids.append(batch.table_oid)
            else:
                all_oids.extend(batch.oids)

        parsed_metrics.extend(result.parsed_metrics)

    return {'all_oids': all_oids, 'bulk_oids': bulk_oids, 'parsed_metrics': parsed_metrics}


def parse_metric(metric):
    # type: (Metric) -> ParseResult
    """
    Parse a single metric in the `metrics` section.

    Can either be:

    * An OID metric:

    ```
    metrics:
      - OID: 1.3.6.1.2.1.2.2.1.14
        name: ifInErrors
    ```

    * A symbol metric:

    ```
    metrics:
      - MIB: IF-MIB
        symbol: ifInErrors
        # OR:
        symbol:
          OID: 1.3.6.1.2.1.2.2.1.14
          name: ifInErrors
    ```

    * A table metric (see `parse_table_metric()` for details):

    ```
    metrics:
      - MIB: IF-MIB
        table: ifTable
        symbols:
          - OID: 1.3.6.1.2.1.2.2.1.14
            name: ifInErrors
    ```
    """

    if 'OID' in metric:
        metric = cast(OIDMetric, metric)
        return parse_oid_metric(metric)

    if 'MIB' not in metric:
        raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

    if 'symbol' in metric:
        metric = cast(SymbolMetric, metric)
        return parse_symbol_metric(metric)

    if 'table' in metric:
        if 'symbols' not in metric:
            raise ConfigurationError('When specifying a table, you must specify a list of symbols')
        metric = cast(TableMetric, metric)
        return parse_table_metric(metric)

    raise ConfigurationError('When specifying a MIB, you must specify either table or symbol')
