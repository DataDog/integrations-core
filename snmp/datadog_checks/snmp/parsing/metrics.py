# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for parsing the `metrics` section of a config file.
"""
import re
from logging import Logger  # noqa: F401
from typing import Dict, List, NamedTuple, Optional, Pattern, Sequence, TypedDict, Union, cast

import six

from datadog_checks.base import ConfigurationError

from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver  # noqa: F401
from .metric_tags import MetricTag, parse_metric_tag
from .metrics_types import (
    ColumnTableMetricTag,
    IndexTableMetricTag,
    Metric,  # noqa: F401
    OIDMetric,
    Symbol,  # noqa: F401
    SymbolMetric,
    TableMetric,
    TableMetricTag,  # noqa: F401
)
from .parsed_metrics import ParsedMetric, ParsedMetricTag, ParsedSymbolMetric, ParsedTableMetric

ParseMetricsResult = TypedDict(
    'ParseMetricsResult',
    {'oids': List[OID], 'next_oids': List[OID], 'bulk_oids': List[OID], 'parsed_metrics': List[ParsedMetric]},
)


def parse_metrics(metrics, resolver, logger, bulk_threshold=0):
    # type: (List[Metric], OIDResolver, Optional[Logger], int) -> ParseMetricsResult
    """
    Parse the `metrics` section of a config file, and return OIDs to fetch and metrics to submit.
    """
    oids = []
    next_oids = []
    bulk_oids = []
    parsed_metrics = []  # type: List[ParsedMetric]

    for metric in metrics:
        result = _parse_metric(metric, logger)

        for oid in result.oids_to_fetch:
            oids.append(oid)

        for name, oid in result.oids_to_resolve.items():
            resolver.register(oid, name)

        for index_mapping in result.index_mappings:
            resolver.register_index(tag=index_mapping.tag, index=index_mapping.index, mapping=index_mapping.mapping)

        for batch in result.table_batches.values():
            should_query_in_bulk = bulk_threshold and len(batch.oids) > bulk_threshold
            if should_query_in_bulk:
                bulk_oids.append(batch.table_oid)
            else:
                # NOTE: we should issue GETNEXT commands for these OIDs, because GET commands on table column OIDs
                # never succeed.
                # This is because data for a given entry in the table is available at the column OIDs **suffixed
                # with the table entry index**, i.e. `<COLUMN_OID>.<ENTRY_INDEX>`. (There's nothing at `<COLUMN_OID>`.)
                next_oids.extend(batch.oids)

        parsed_metrics.extend(result.parsed_metrics)

    return {'oids': oids, 'next_oids': next_oids, 'bulk_oids': bulk_oids, 'parsed_metrics': parsed_metrics}


# Helpers below.
# NOTE: most type definitions below are for containers of intermediary parsed data - not related to config file format.

IndexMapping = NamedTuple('IndexMapping', [('tag', str), ('index', int), ('mapping', dict)])
TableBatchKey = NamedTuple('TableBatchKey', [('mib', str), ('table', str)])
TableBatch = NamedTuple('TableBatch', [('table_oid', OID), ('oids', List[OID])])
TableBatches = Dict[TableBatchKey, TableBatch]

MetricParseResult = NamedTuple(
    'MetricParseResult',
    [
        ('oids_to_fetch', List[OID]),
        ('oids_to_resolve', Dict[str, OID]),
        ('index_mappings', List[IndexMapping]),
        ('table_batches', TableBatches),
        ('parsed_metrics', Sequence[ParsedMetric]),
    ],
)


def _parse_metric(metric, logger):
    # type: (Metric, Optional[Logger]) -> MetricParseResult
    """
    Parse a single metric in the `metrics` section of a config file.

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

    * A table metric (see parsing for table metrics for all possible options):

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
        return _parse_oid_metric(metric)

    if 'MIB' not in metric:
        raise ConfigurationError('Unsupported metric in config file: {}'.format(metric))

    if 'symbol' in metric:
        metric = cast(SymbolMetric, metric)
        return _parse_symbol_metric(metric)

    if 'table' in metric:
        if 'symbols' not in metric:
            raise ConfigurationError('When specifying a table, you must specify a list of symbols')
        metric = cast(TableMetric, metric)
        return _parse_table_metric(metric, logger)

    raise ConfigurationError('When specifying a MIB, you must specify either a table or a symbol')


def _parse_oid_metric(metric):
    # type: (OIDMetric) -> MetricParseResult
    """
    Parse a fully resolved OID/name metric.

    Note: This `OID/name` syntax is deprecated in favour of `symbol` syntax.

    Example:

    ```
    metrics:
      - OID: 1.3.6.1.2.1.2.1
        name: ifNumber
    ```
    """
    name = metric['name']
    oid = OID(metric['OID'])

    parsed_symbol_metric = ParsedSymbolMetric(
        name,
        tags=metric.get('metric_tags', []),
        forced_type=metric.get('forced_type'),
        enforce_scalar=False,
        options=metric.get('options', {}),
    )

    return MetricParseResult(
        oids_to_fetch=[oid],
        oids_to_resolve={name: oid},
        parsed_metrics=[parsed_symbol_metric],
        index_mappings=[],
        table_batches={},
    )


def _parse_symbol_metric(metric):
    # type: (SymbolMetric) -> MetricParseResult
    """
    Parse a symbol metric (= an OID in a MIB).

    Example:

    ```
    metrics:
      - MIB: IF-MIB
        symbol: <string or OID/name object>
      - MIB: IF-MIB
        symbol:                     # MIB-less syntax
          OID: 1.3.6.1.2.1.6.5.0
          name: tcpActiveOpens
      - MIB: IF-MIB
        symbol: tcpActiveOpens      # require MIB syntax
    ```
    """
    mib = metric['MIB']
    symbol = metric['symbol']

    parsed_symbol = _parse_symbol(mib, symbol)

    parsed_symbol_metric = ParsedSymbolMetric(
        parsed_symbol.name,
        tags=metric.get('metric_tags', []),
        forced_type=metric.get('forced_type'),
        options=metric.get('options', {}),
        extract_value_pattern=parsed_symbol.extract_value_pattern,
    )

    return MetricParseResult(
        oids_to_fetch=[parsed_symbol.oid],
        oids_to_resolve=parsed_symbol.oids_to_resolve,
        parsed_metrics=[parsed_symbol_metric],
        index_mappings=[],
        table_batches={},
    )


ParsedSymbol = NamedTuple(
    'ParsedSymbol',
    [('name', str), ('oid', OID), ('extract_value_pattern', Optional[Pattern]), ('oids_to_resolve', Dict[str, OID])],
)


def _parse_symbol(mib, symbol):
    # type: (str, Union[str, Symbol]) -> ParsedSymbol
    """
    Parse an OID symbol.

    This can either be the unresolved name of a symbol:

    ```
    symbol: ifNumber
    ```

    Or a resolved OID/name object:

    ```
    symbol:
        OID: 1.3.6.1.2.1.2.1
        name: ifNumber
    ```
    """
    if isinstance(symbol, str):
        oid = OID(ObjectIdentity(mib, symbol))
        return ParsedSymbol(name=symbol, oid=oid, extract_value_pattern=None, oids_to_resolve={})

    oid = OID(symbol['OID'])
    name = symbol['name']

    extract_value = symbol.get('extract_value')
    extract_value_pattern = None
    if extract_value:
        try:
            extract_value_pattern = re.compile(extract_value)
        except re.error as exc:
            raise ConfigurationError('Failed to compile regular expression {!r}: {}'.format(extract_value, exc))

    return ParsedSymbol(name=name, oid=oid, extract_value_pattern=extract_value_pattern, oids_to_resolve={name: oid})


def _parse_table_metric(metric, logger):
    # type: (TableMetric, Optional[Logger]) -> MetricParseResult
    mib = metric['MIB']

    parsed_table = _parse_symbol(mib, metric['table'])
    oids_to_resolve = parsed_table.oids_to_resolve

    # Parse metric tags first, as we need the list of index tags and column tags.
    # Column metric tags may specify other OIDs to fetch, so make sure to keep track of them.

    index_tags = []
    column_tags = []
    index_mappings = []
    table_batches = {}  # type: TableBatches

    if metric.get('metric_tags'):
        for metric_tag in metric['metric_tags']:
            parsed_table_metric_tag = _parse_table_metric_tag(mib, parsed_table, metric_tag)

            if isinstance(parsed_table_metric_tag, ParsedColumnMetricTag):
                oids_to_resolve.update(parsed_table_metric_tag.oids_to_resolve)
                column_tags.extend(parsed_table_metric_tag.column_tags)
                table_batches = merge_table_batches(table_batches, parsed_table_metric_tag.table_batches)

            else:
                index_tags.extend(parsed_table_metric_tag.index_tags)

                for index, mapping in parsed_table_metric_tag.index_mappings.items():
                    # Need to do manual resolution.
                    for symbol in metric['symbols']:
                        index_mappings.append(IndexMapping(symbol['name'], index=index, mapping=mapping))

                    for tag in metric.get('metric_tags', []):
                        if 'column' in tag:
                            tag = cast(ColumnTableMetricTag, tag)
                            index_mappings.append(IndexMapping(tag['column']['name'], index=index, mapping=mapping))
    elif logger:
        logger.warning(
            "%s table doesn't have a 'metric_tags' section, all its metrics will use the same tags. "
            "If the table has multiple rows, only one row will be submitted. "
            "Please add at least one discriminating metric tag (such as a row index) "
            "to ensure metrics of all rows are submitted.",
            str(metric['table']),
        )

    # Then process symbols in the table.

    table_oids = []
    parsed_metrics = []

    for symbol in metric['symbols']:
        parsed_symbol = _parse_symbol(mib, symbol)
        oids_to_resolve.update(parsed_symbol.oids_to_resolve)

        table_oids.append(parsed_symbol.oid)

        parsed_table_metric = ParsedTableMetric(
            parsed_symbol.name,
            index_tags=index_tags,
            column_tags=column_tags,
            forced_type=metric.get('forced_type'),
            options=metric.get('options', {}),
            extract_value_pattern=parsed_symbol.extract_value_pattern,
        )
        parsed_metrics.append(parsed_table_metric)

    table_batches = merge_table_batches(
        table_batches, {TableBatchKey(mib, table=parsed_table.name): TableBatch(parsed_table.oid, oids=table_oids)}
    )

    return MetricParseResult(
        oids_to_fetch=[],
        oids_to_resolve=oids_to_resolve,
        table_batches=table_batches,
        index_mappings=index_mappings,
        parsed_metrics=parsed_metrics,
    )


def merge_table_batches(target, source):
    # type: (TableBatches, TableBatches) -> TableBatches
    merged = {}

    # Extend batches in `target` with OIDs from `source` that share the same key.
    for key in target:
        batch = target[key]
        if key in source:
            batch = TableBatch(batch.table_oid, oids=batch.oids + source[key].oids)
        merged[key] = batch

    # Add the rest of batches in `source`.
    for key in source:
        if key not in target:
            merged[key] = source[key]

    return merged


IndexTag = NamedTuple('IndexTag', [('parsed_metric_tag', ParsedMetricTag), ('index', int)])
ColumnTag = NamedTuple(
    'ColumnTag',
    [('parsed_metric_tag', ParsedMetricTag), ('column', str), ('index_slices', List[slice])],
)

ParsedColumnMetricTag = NamedTuple(
    'ParsedColumnMetricTag',
    [('oids_to_resolve', Dict[str, OID]), ('table_batches', TableBatches), ('column_tags', List[ColumnTag])],
)

ParsedIndexMetricTag = NamedTuple(
    'ParsedIndexMetricTag', [('index_tags', List[IndexTag]), ('index_mappings', Dict[int, dict])]
)

ParsedTableMetricTag = Union[ParsedColumnMetricTag, ParsedIndexMetricTag]


def _parse_table_metric_tag(mib, parsed_table, metric_tag):
    # type: (str, ParsedSymbol, TableMetricTag) -> ParsedTableMetricTag
    """
    Parsed an item of the `metric_tags` section of a table metric.

    Items can be:

    * A reference to a column in the same table.

    Example using entPhySensorTable in ENTITY-SENSOR-MIB:

    ```
    metric_tags:
      - tag: sensor_type
        column: entPhySensorType
        # OR
        column:
        OID: 1.3.6.1.2.1.99.1.1.1.1
        name: entPhySensorType
    ```

    * A reference to a column in a different table.

    Example:

    ```
    metric_tags:
      - tag: adapter
        table: genericAdaptersAttrTable
        column: adapterName
        # OR
        column:
          OID: 1.3.6.1.4.1.343.2.7.2.2.1.1.1.2
          name: adapterName
    ```

    * A reference to an OID by its index in the table entry.

    An optional `mapping` can be used to map index values to human-readable strings.

    Example using ipIfStatsTable in IP-MIB:

    ```
    metric_tags:
      - # ipIfStatsIPVersion (1.3.6.1.2.1.4.21.3.1.1)
        tag: ip_version
        index: 1
        mapping:
          0: unknown
          1: ipv4
          2: ipv6
          3: ipv4z
          4: ipv6z
          16: dns
      - # ipIfStatsIfIndex (1.3.6.1.2.1.4.21.3.1.2)
        tag: interface
        index: 2
    ```
    """
    if 'column' in metric_tag:
        metric_tag = cast(ColumnTableMetricTag, metric_tag)
        metric_tag_mib = metric_tag.get('MIB', mib)

        if 'table' in metric_tag:
            return _parse_other_table_column_metric_tag(metric_tag_mib, metric_tag['table'], metric_tag)

        if mib != metric_tag_mib:
            raise ConfigurationError('When tagging from a different MIB, the table must be specified')

        return _parse_column_metric_tag(mib, parsed_table, metric_tag)

    if 'index' in metric_tag:
        metric_tag = cast(IndexTableMetricTag, metric_tag)
        return _parse_index_metric_tag(metric_tag)

    raise ConfigurationError('When specifying metric tags, you must specify either and index or a column')


def _parse_column_metric_tag(mib, parsed_table, metric_tag):
    # type: (str, ParsedSymbol, ColumnTableMetricTag) -> ParsedColumnMetricTag
    parsed_column = _parse_symbol(mib, metric_tag['column'])

    batches = {TableBatchKey(mib, table=parsed_table.name): TableBatch(parsed_table.oid, oids=[parsed_column.oid])}

    return ParsedColumnMetricTag(
        oids_to_resolve=parsed_column.oids_to_resolve,
        column_tags=[
            ColumnTag(
                parsed_metric_tag=parse_metric_tag(cast(MetricTag, metric_tag)),
                column=parsed_column.name,
                index_slices=_parse_index_slices(metric_tag),
            )
        ],
        table_batches=batches,
    )


def _parse_other_table_column_metric_tag(mib, table, metric_tag):
    # type: (str, str, ColumnTableMetricTag) -> ParsedTableMetricTag
    parsed_table = _parse_symbol(mib, table)
    parsed_metric_tag = _parse_column_metric_tag(mib, parsed_table, metric_tag)

    oids_to_resolve = parsed_metric_tag.oids_to_resolve
    oids_to_resolve.update(parsed_table.oids_to_resolve)

    return ParsedColumnMetricTag(
        oids_to_resolve=oids_to_resolve,
        table_batches=parsed_metric_tag.table_batches,
        column_tags=parsed_metric_tag.column_tags,
    )


def _parse_index_metric_tag(metric_tag):
    # type: (IndexTableMetricTag) -> ParsedTableMetricTag
    index_tags = [IndexTag(parsed_metric_tag=parse_metric_tag(cast(MetricTag, metric_tag)), index=metric_tag['index'])]
    index_mappings = {metric_tag['index']: metric_tag['mapping']} if 'mapping' in metric_tag else {}

    return ParsedIndexMetricTag(index_tags=index_tags, index_mappings=index_mappings)


def _parse_index_slices(metric_tag):
    # type: (ColumnTableMetricTag) -> List[slice]
    """
    Transform index_transform into list of index slices.

    `index_transform` is needed to support tagging using another table with different indexes.

    Example: TableB have two indexes indexX (1 digit) and indexY (3 digits).
        We want to tag by an external TableA that have indexY (3 digits).

        For example TableB has a row with full index `1.2.3.4`, indexX is `1` and indexY is `2.3.4`.
        TableA has a row with full index `2.3.4`, indexY is `2.3.4` (matches indexY of TableB).

        SNMP integration doesn't know how to compare the full indexes from TableB and TableA.
        We need to extract a subset of the full index of TableB to match with TableA full index.

        Using the below `index_transform` we provide enough info to extract a subset of index that
        will be used to match TableA's full index.

        ```yaml
        index_transform:
          - start: 1
          - end: 3
        ```
    """
    raw_index_slices = metric_tag.get('index_transform')
    index_slices = []  # type: List[slice]

    if raw_index_slices:
        for rule in raw_index_slices:
            if not isinstance(rule, dict) or set(rule) != {'start', 'end'}:
                raise ConfigurationError('Transform rule must contain start and end. Invalid rule: {}'.format(rule))
            start, end = rule['start'], rule['end']
            if not isinstance(start, six.integer_types) or not isinstance(end, six.integer_types):
                raise ConfigurationError('Transform rule start and end must be integers. Invalid rule: {}'.format(rule))
            if start > end:
                raise ConfigurationError(
                    'Transform rule end should be greater than start. Invalid rule: {}'.format(rule)
                )
            if start < 0:
                raise ConfigurationError('Transform rule start must be greater than 0. Invalid rule: {}'.format(rule))
            # For a better user experience, the `end` in metrics definition is inclusive.
            # We +1 to `end` since the `end` in python slices is exclusive.
            index_slices.append(slice(start, end + 1))

    return index_slices
