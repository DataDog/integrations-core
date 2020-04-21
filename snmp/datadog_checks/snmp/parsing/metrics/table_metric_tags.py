# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Dict, List, cast

from datadog_checks.base import ConfigurationError

from ...models import OID
from .symbols import parse_symbol
from .types import (
    ColumnTableMetricTag,
    ColumnTag,
    IndexTableMetricTag,
    IndexTag,
    TableBatch,
    TableBatches,
    TableBatchKey,
    TableMetricTag,
)


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


def parse_index_metric_tag(metric_tag):
    # type: (IndexTableMetricTag) -> ParsedTableMetricTag
    index_tags = [IndexTag(name=metric_tag['tag'], index=metric_tag['index'])]
    index_mappings_to_register = {metric_tag['index']: metric_tag['mapping']} if 'mapping' in metric_tag else None

    return ParsedTableMetricTag(index_tags=index_tags, index_mappings_to_register=index_mappings_to_register)


def parse_column_metric_tag(metric_tag, mib):
    # type: (ColumnTableMetricTag, str) -> ParsedTableMetricTag
    parsed_column = parse_symbol(metric_tag.get('MIB', mib), metric_tag['column'])

    return ParsedTableMetricTag(
        oids_to_fetch=[parsed_column.oid],
        oids_to_resolve=parsed_column.oids_to_resolve,
        column_tags=[ColumnTag(name=metric_tag['tag'], column=parsed_column.name)],
    )


def parse_other_table_column_metric_tag(metric_tag, mib, table):
    # type: (ColumnTableMetricTag, str, str) -> ParsedTableMetricTag
    parsed_metric_tag = parse_column_metric_tag({'tag': metric_tag['tag'], 'column': metric_tag['column']}, mib=mib)

    column_oid = parsed_metric_tag.oids_to_fetch[0]
    oids_to_resolve = parsed_metric_tag.oids_to_resolve

    parsed_table = parse_symbol(mib, table)
    oids_to_resolve.update(parsed_table.oids_to_resolve)

    return ParsedTableMetricTag(
        oids_to_fetch=[column_oid],
        oids_to_resolve=oids_to_resolve,
        table_batches={TableBatchKey(mib, parsed_table.name): TableBatch(parsed_table.oid, oids=[column_oid])},
        column_tags=parsed_metric_tag.column_tags,
    )
