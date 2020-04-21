# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import cast

from ..parsed_metrics import ParsedTableMetric
from .models import ParseResult
from .symbols import parse_symbol
from .table_metric_tags import parse_table_metric_tag
from .types import ColumnTableMetricTag, IndexMapping, TableBatch, TableBatches, TableBatchKey, TableMetric


def parse_table_metric(metric):
    # type: (TableMetric) -> ParseResult
    mib = metric['MIB']

    parsed_table = parse_symbol(mib, metric['table'])
    oids_to_resolve = parsed_table.oids_to_resolve

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

        for index, mapping in parsed_table_metric_tag.index_mappings.items():
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
        oids_to_resolve.update(parsed_symbol.oids_to_resolve)

        table_oids.append(parsed_symbol.oid)

        parsed_table_metric = ParsedTableMetric(
            parsed_symbol.name,
            index_tags=[(tag.name, tag.index) for tag in index_tags],
            column_tags=[(tag.name, tag.column) for tag in column_tags],
            forced_type=metric.get('forced_type'),
        )
        parsed_metrics.append(parsed_table_metric)

    table_batches = merge_table_batches(
        table_batches, {TableBatchKey(mib, table=parsed_table.name): TableBatch(parsed_table.oid, oids=table_oids)}
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
