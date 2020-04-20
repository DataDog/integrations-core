# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import List, Tuple, Union, cast

from datadog_checks.base import ConfigurationError

from ..models import OID
from .extractor import MetricExtractor
from .models import ParsedTableMetric
from .types import ColumnMetricTag, IndexMetricTag, MetricTag, Symbol, TableMetric


def parse_table_metric(extractor, metric):
    # type: (MetricExtractor, TableMetric) -> List[ParsedTableMetric]

    # NOTE: it is currently critical that `symbols` is a mutable reference to the list of symbols for this table.
    # Ideally we should find a way to not rely on mutability here...
    symbols, _ = extractor.extract_table_symbols(metric['MIB'], metric['table'])

    table_ctx = TableParseContext(extractor, metric, symbols)

    # Parse metric tags first, so that any index/column tags are appropriately
    # applied to all symbol parsed metrics.
    for metric_tag in metric.get('metric_tags', []):
        _parse_table_metric_tag(table_ctx, metric_tag)

    return [_parse_table_symbol(table_ctx, symbol) for symbol in metric['symbols']]


# Helpers.


class TableParseContext(object):
    """
    Container for state accumulated while parsing a table metric.
    """

    def __init__(self, extractor, metric, symbols):
        # type: (MetricExtractor, TableMetric, List[OID]) -> None
        self.extractor = extractor
        self.metric = metric
        self.symbols = symbols
        self.index_tags = []  # type: List[Tuple[str, int]]
        self.column_tags = []  # type: List[Tuple[str, str]]


def _parse_table_symbol(table_ctx, symbol):
    # type: (TableParseContext, Union[str, Symbol]) -> ParsedTableMetric
    oid, parsed_metric_name = table_ctx.extractor.extract_symbol(table_ctx.metric['MIB'], symbol)
    table_ctx.symbols.append(oid)
    parsed_metric = ParsedTableMetric(
        name=parsed_metric_name,
        index_tags=table_ctx.index_tags,
        column_tags=table_ctx.column_tags,
        forced_type=table_ctx.metric.get('forced_type'),
    )
    return parsed_metric


def _parse_table_metric_tag(ctx, metric_tag):
    # type: (TableParseContext, MetricTag) -> None
    if not ('tag' in metric_tag and ('index' in metric_tag or 'column' in metric_tag)):
        raise ConfigurationError('When specifying metric tags, you must specify a tag, and an index or column')

    if 'index' in metric_tag:
        metric_tag = cast(IndexMetricTag, metric_tag)
        _parse_index_metric_tag(ctx, metric_tag)

    elif 'column' in metric_tag:
        metric_tag = cast(ColumnMetricTag, metric_tag)
        _parse_column_metric_tag(ctx, metric_tag)


def _parse_index_metric_tag(ctx, metric_tag):
    # type: (TableParseContext, IndexMetricTag) -> None
    ctx.index_tags.append((metric_tag['tag'], metric_tag['index']))

    if 'mapping' in metric_tag:
        # Need to do manual resolution.
        _register_index_mapping(ctx, index=metric_tag['index'], mapping=metric_tag['mapping'])


def _register_index_mapping(ctx, index, mapping):
    # type: (TableParseContext, int, dict) -> None
    for symbol in ctx.metric['symbols']:
        ctx.extractor.register_index(symbol['name'], index=index, mapping=mapping)

    for tag in ctx.metric.get('metric_tags', []):
        if 'column' in tag:
            tag = cast(ColumnMetricTag, tag)
            ctx.extractor.register_index(tag['column']['name'], index=index, mapping=mapping)


def _parse_column_metric_tag(ctx, metric_tag):
    # type: (TableParseContext, ColumnMetricTag) -> None
    mib = metric_tag.get('MIB', ctx.metric['MIB'])

    # We need to query OIDs for columns too.
    oid, column = ctx.extractor.extract_symbol(mib, metric_tag['column'])

    ctx.column_tags.append((metric_tag['tag'], column))

    if 'table' in metric_tag:
        # Different table.
        tag_symbols, _ = ctx.extractor.extract_table_symbols(mib, metric_tag['table'])
        tag_symbols.append(oid)
    elif mib != ctx.metric['MIB']:
        raise ConfigurationError('When tagging from a different MIB, the table must be specified')
    else:
        ctx.symbols.append(oid)
