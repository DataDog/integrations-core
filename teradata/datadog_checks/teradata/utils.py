# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from typing import Any, AnyStr, Sequence, Set, Tuple  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.teradata.config_models.instance import Table


def filter_tables(tables_filter, row):
    # type: (Any, Sequence) -> Sequence
    tables_to_collect, tables_to_exclude = tables_filter
    table_name = row[3]
    # No tables filter
    if not tables_to_collect and not tables_to_exclude:
        return row
    # Table filtered out
    if table_name in tables_to_exclude:
        return []
    # Table included
    if table_name in tables_to_collect:
        return row
    # Table excluded
    return []


def create_tables_filter(tables):
    # type: (Any) -> Tuple[Set, Set]

    tables_to_collect = set()
    tables_to_exclude = set()

    if isinstance(tables, tuple):
        tables_to_collect = set(tables)
        return tables_to_collect, tables_to_exclude

    if isinstance(tables, Table):
        if tables.include and tables.exclude:
            for table in tables.include:
                if table not in tables.exclude:
                    tables_to_collect.add(table)
            tables_to_exclude = set(tables.exclude)
            return tables_to_collect, tables_to_exclude

        if tables.include:
            tables_to_collect = set(tables.include)

        if tables.exclude:
            tables_to_exclude = set(tables.exclude)

        return (tables_to_collect, tables_to_exclude)


def timestamp_validator(check, row):
    # type: (Any, Sequence) -> Sequence
    now = time.time()
    row_ts = row[0]
    if type(row_ts) is not int:
        msg = 'Returned timestamp `{}` is invalid.'.format(row_ts)
        check.log.warning(msg)
        check._query_errors += 1
        return []
    diff = now - row_ts
    # Valid metrics should be no more than 10 min in the future or 1h in the past
    if (diff > 3600) or (diff < -600):
        msg = 'Resource Usage stats are invalid. {}'
        if diff > 3600:
            msg = msg.format('Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?')
        elif diff < -600:
            msg = msg.format('Row timestamp is more than 10 min in the future. Try checking system time settings.')
        check.log.warning(msg)
        check._query_errors += 1
        return []
    return row


def tags_normalizer(row, query_name):
    # type: (Any, Sequence, AnyStr) -> Sequence
    base_tags = [{"name": "td_amp", "col": row[0]}, {"name": "td_account", "col": row[1]}]
    tags_map = [
        {"stats_name": "DBC.DiskSpaceV", "tags": base_tags + [{"name": "td_database", "col": row[2]}]},
        {
            "stats_name": "DBC.AllSpaceV",
            "tags": base_tags + [{"name": "td_database", "col": row[2]}, {"name": "td_table", "col": row[3]}],
        },
        {
            "stats_name": "DBC.AMPUsageV",
            "tags": base_tags + [{"name": "td_user", "col": row[2]}],
        },
    ]

    for stats_type in tags_map:
        if query_name == stats_type['stats_name']:
            for idx, tag in enumerate(stats_type['tags']):
                # tag value may be type int
                if not len(str(tag['col'])):
                    row[idx] = "undefined"
    return row


@AgentCheck.metadata_entrypoint
def submit_version(check, row):
    # type (Any) -> None
    """
    Example version: 17.10.03.01
    https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/DBCInfoV/Example-Using-DBCInfoV
    """
    try:
        teradata_version = row[0]
        version_parts = {
            name: part for name, part in zip(('major', 'minor', 'maintenance', 'patch'), teradata_version.split('.'))
        }
        check.set_metadata('version', teradata_version, scheme='parts', final_scheme='semver', part_map=version_parts)
    except Exception as e:
        check.log.warning("Could not collect version info: %s", e)
