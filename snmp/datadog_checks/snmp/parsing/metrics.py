# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers to parse the `metrics` section of a config file.
"""
from typing import Dict, List, NamedTuple, Sequence, TypedDict, Union, cast

from datadog_checks.base import ConfigurationError

from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver
from .parsed_metrics import ParsedMetric, ParsedSymbolMetric, ParsedTableMetric

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


# Helpers.


class ParseResult(object):
    def __init__(
        self,
        oids_to_fetch=None,  # type: List[OID]
        oids_to_resolve=None,  # type: Dict[str, OID]
        table_batches=None,  # type: TableBatches
        index_mappings=None,  # type: List[IndexMapping]
        parsed_metrics=None,  # type: Sequence[ParsedMetric]
    ):
        # type: (...) -> None
        self.oids_to_fetch = oids_to_fetch or []
        self.oids_to_resolve = oids_to_resolve or {}
        self.table_batches = table_batches or {}
        self.index_mappings = index_mappings or []
        self.parsed_metrics = parsed_metrics or []


class ParsedTable(object):
    def __init__(self, name, oid, oids_to_resolve=None):
        # type: (str, OID, Dict[str, OID]) -> None
        self.name = name
        self.oid = oid
        self.oids_to_resolve = oids_to_resolve or {}


Metric = Union["OIDMetric", "SymbolMetric", "TableMetric"]


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


OIDMetric = TypedDict(
    'OIDMetric', {'name': str, 'OID': str, 'metric_tags': List[str], 'forced_type': str}, total=False,
)


def parse_oid_metric(metric):
    # type: (OIDMetric) -> ParseResult
    name = metric['name']
    oid = OID(metric['OID'])

    parsed_symbol_metric = ParsedSymbolMetric(
        name, tags=metric.get('metric_tags', []), forced_type=metric.get('forced_type'), enforce_scalar=False
    )

    return ParseResult(oids_to_fetch=[oid], oids_to_resolve={name: oid}, parsed_metrics=[parsed_symbol_metric])


Symbol = TypedDict('Symbol', {'OID': str, 'name': str})
SymbolMetric = TypedDict(
    'SymbolMetric',
    {'MIB': str, 'symbol': Union[str, Symbol], 'forced_type': str, 'metric_tags': List[str]},
    total=False,
)


class ParsedSymbol(object):
    def __init__(self, name, oid, should_resolve):
        # type: (str, OID, bool) -> None
        self.name = name
        self.oid = oid
        self.should_resolve = should_resolve


def parse_symbol(mib, symbol):
    # type: (str, Union[str, Symbol]) -> ParsedSymbol
    """
    Parse an OID symbol.

    This can either be the unresolved name of a symbol:

    ```
    symbol: ifInErrors
    ```

    Or a resolved {OID, name} object:

    ```
    symbol:
        OID: 1.3.6.1.2.1.2.2.1.14
        name: ifInErrors
    ```
    """
    if isinstance(symbol, str):
        oid = OID(ObjectIdentity(mib, symbol))
        return ParsedSymbol(name=symbol, oid=oid, should_resolve=False)

    oid = OID(symbol['OID'])
    name = symbol['name']
    return ParsedSymbol(name=name, oid=oid, should_resolve=True)


def parse_symbol_metric(metric):
    # type: (SymbolMetric) -> ParseResult
    mib = metric['MIB']
    symbol = metric['symbol']

    parsed_symbol = parse_symbol(mib, symbol)
    name = parsed_symbol.name

    parsed_symbol_metric = ParsedSymbolMetric(
        name, tags=metric.get('metric_tags', []), forced_type=metric.get('forced_type')
    )

    return ParseResult(
        oids_to_fetch=[parsed_symbol.oid],
        oids_to_resolve={name: parsed_symbol.oid} if parsed_symbol.should_resolve else None,
        parsed_metrics=[parsed_symbol_metric],
    )


TableMetric = TypedDict(
    'TableMetric',
    {
        'MIB': str,
        'table': Union[str, Symbol],
        'symbols': List[Symbol],
        'forced_type': str,
        'metric_tags': List["TableMetricTag"],
    },
    total=False,
)
TableBatchKey = NamedTuple('TableBatchKey', [('mib', str), ('name', str)])
TableBatch = NamedTuple('TableBatch', [('table_oid', OID), ('oids', List[OID])])
TableBatches = Dict[TableBatchKey, TableBatch]
IndexMapping = NamedTuple('IndexMapping', [('tag', str), ('index', int), ('mapping', dict)])


def parse_table_metric(metric):
    # type: (TableMetric) -> ParseResult
    mib = metric['MIB']

    parsed_table = parse_symbol(mib, metric['table'])
    oids_to_resolve = {parsed_table.name: parsed_table.oid} if parsed_table.should_resolve else {}

    # Parse metric tags first, as we need the list of index tags and column tags.
    # Column metric tags may specify other OIDs to fetch, so make sure to keep track of them.

    other_oids_to_fetch = []
    index_tags = []
    column_tags = []
    index_mappings = []
    table_batches = {}  # type: TableBatches

    for metric_tag in metric.get('metric_tags', []):
        parsed_table_metric_tag = parse_table_metric_tag(mib, metric_tag)

        other_oids_to_fetch.extend(parsed_table_metric_tag.oids_to_fetch)
        oids_to_resolve.update(parsed_table_metric_tag.oids_to_resolve)
        index_tags.extend(parsed_table_metric_tag.index_tags)
        column_tags.extend(parsed_table_metric_tag.column_tags)
        table_batches = merge_table_batches(table_batches, parsed_table_metric_tag.table_batches)

        for index, mapping in parsed_table_metric_tag.index_mappings_to_register.items():
            # Need to do manual resolution.
            for symbol in metric['symbols']:
                index_mappings.append(IndexMapping(symbol['name'], index=index, mapping=mapping))

            for tag in metric.get('metric_tags', []):
                if 'column' in tag:
                    tag = cast(ColumnTableMetricTag, tag)
                    index_mappings.append(IndexMapping(tag['column']['name'], index=index, mapping=mapping))

    # Then process symbols in the table.

    table_oids = []
    parsed_metrics = []

    for symbol in metric['symbols']:
        parsed_symbol = parse_symbol(mib, symbol)
        name = parsed_symbol.name

        if parsed_symbol.should_resolve:
            oids_to_resolve[name] = parsed_symbol.oid

        table_oids.append(parsed_symbol.oid)

        parsed_table_metric = ParsedTableMetric(
            name,
            index_tags=[(tag.name, tag.index) for tag in index_tags],
            column_tags=[(tag.name, tag.column) for tag in column_tags],
            forced_type=metric.get('forced_type'),
        )

        parsed_metrics.append(parsed_table_metric)

    table_batches = merge_table_batches(
        table_batches, {TableBatchKey(mib, parsed_table.name): TableBatch(parsed_table.oid, oids=table_oids)}
    )

    return ParseResult(
        oids_to_fetch=other_oids_to_fetch,
        oids_to_resolve=oids_to_resolve,
        table_batches=table_batches,
        index_mappings=index_mappings,
        parsed_metrics=parsed_metrics,
    )


def merge_table_batches(target, source):
    # type: (TableBatches, TableBatches) -> TableBatches
    merged = {}

    # Extend batches in `target` with OIDs from `source` that share the same keu.
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


TableMetricTag = Union["IndexTableMetricTag", "ColumnTableMetricTag"]
IndexTag = NamedTuple('IndexTag', [('name', str), ('index', int)])
ColumnTag = NamedTuple('ColumnTag', [('name', str), ('column', str)])


class ParsedTableMetricTag(object):
    def __init__(
        self,
        oids_to_fetch=None,  # type: List[OID]
        oids_to_resolve=None,  # type: Dict[str, OID]
        table_batches=None,  # type: TableBatches
        index_tags=None,  # type: List[IndexTag]
        column_tags=None,  # type: List[ColumnTag]
        index_mappings_to_register=None,  # type: Dict[int, dict]
    ):
        # type: (...) -> None
        self.oids_to_fetch = oids_to_fetch or []
        self.oids_to_resolve = oids_to_resolve or {}
        self.table_batches = table_batches or {}
        self.index_tags = index_tags or []
        self.column_tags = column_tags or []
        self.index_mappings_to_register = index_mappings_to_register or {}


def parse_table_metric_tag(mib, metric_tag):
    # type: (str, TableMetricTag) -> ParsedTableMetricTag
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

    * A reference to an column that contains an integer index.

    An optional `mapping` can be used to map index values to human-readable strings.
    Examples using ipIfStatsTable in IP-MIB:

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
    if 'tag' not in metric_tag:
        raise ConfigurationError('When specifying metric tags, you must specify a tag')

    if 'index' in metric_tag:
        metric_tag = cast(IndexTableMetricTag, metric_tag)
        return parse_index_metric_tag(metric_tag)

    if 'column' in metric_tag:
        metric_tag = cast(ColumnTableMetricTag, metric_tag)
        metric_tag_mib = metric_tag.get('MIB', mib)

        if 'table' in metric_tag:
            return parse_other_table_column_metric_tag(metric_tag, mib=metric_tag_mib, table=metric_tag['table'])

        if mib != metric_tag_mib:
            raise ConfigurationError('When tagging from a different MIB, the table must be specified')

        return parse_column_metric_tag(metric_tag, mib=mib)

    raise ConfigurationError('When specifying metric tags, you must specify either and index or a column')


IndexTableMetricTag = TypedDict(
    'IndexTableMetricTag', {'index': int, 'mapping': Dict[int, str], 'tag': str}, total=False
)


def parse_index_metric_tag(metric_tag):
    # type: (IndexTableMetricTag) -> ParsedTableMetricTag
    index_tags = [IndexTag(name=metric_tag['tag'], index=metric_tag['index'])]
    index_mappings_to_register = {metric_tag['index']: metric_tag['mapping']} if 'mapping' in metric_tag else None

    return ParsedTableMetricTag(index_tags=index_tags, index_mappings_to_register=index_mappings_to_register)


ColumnTableMetricTag = TypedDict(
    'ColumnTableMetricTag', {'MIB': str, 'column': Symbol, 'table': str, 'tag': str}, total=False
)


def parse_column_metric_tag(metric_tag, mib):
    # type: (ColumnTableMetricTag, str) -> ParsedTableMetricTag
    parsed_column = parse_symbol(metric_tag.get('MIB', mib), metric_tag['column'])

    return ParsedTableMetricTag(
        oids_to_fetch=[parsed_column.oid],
        oids_to_resolve={parsed_column.name: parsed_column.oid} if parsed_column.should_resolve else None,
        column_tags=[ColumnTag(name=metric_tag['tag'], column=parsed_column.name)],
    )


def parse_other_table_column_metric_tag(metric_tag, mib, table):
    # type: (ColumnTableMetricTag, str, str) -> ParsedTableMetricTag
    parsed_metric_tag = parse_column_metric_tag({'tag': metric_tag['tag'], 'column': metric_tag['column']}, mib=mib)

    column_oid = parsed_metric_tag.oids_to_fetch[0]
    oids_to_resolve = parsed_metric_tag.oids_to_resolve

    parsed_table = parse_symbol(mib, table)

    if parsed_table.should_resolve:
        oids_to_resolve[parsed_table.name] = parsed_table.oid

    return ParsedTableMetricTag(
        oids_to_fetch=[column_oid],
        oids_to_resolve=oids_to_resolve,
        table_batches={TableBatchKey(mib, parsed_table.name): TableBatch(parsed_table.oid, oids=[column_oid])},
        column_tags=parsed_metric_tag.column_tags,
    )
