# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time


def filter_tables(self, row):
    tables_to_collect, tables_to_exclude = self._tables_filter
    table_name = row[3]

    if not tables_to_collect and not tables_to_exclude:
        return row
    if table_name in tables_to_exclude:
        return []
    if table_name in tables_to_collect:
        return row
    return []


def create_tables_filter(self):
    """
    List of strings
    Mapping of `include` (list of strings) and `exclude` (list of strings)
    """
    tables_to_collect = set()
    tables_to_exclude = set()

    tables = self.config.tables

    if isinstance(tables, list):
        tables_to_collect = set(tables)

    if isinstance(tables, dict):
        include_tables = tables.get('include')
        exclude_tables = tables.get('exclude')

        if include_tables and exclude_tables:
            for table in include_tables:
                if table not in exclude_tables:
                    tables_to_collect.add(table)
            tables_to_exclude = set(exclude_tables)
            return tables_to_collect, tables_to_exclude

        if include_tables:
            tables_to_collect = set(include_tables)

        if exclude_tables:
            tables_to_exclude = set(exclude_tables)

    return tables_to_collect, tables_to_exclude


def timestamp_validator(self, row):
    # Only rows returned from the Resource Usage table include timestamps
    now = time.time()
    row_ts = row[0]
    if type(row_ts) is not int:
        msg = 'Returned timestamp `{}` is invalid.'.format(row_ts)
        self.log.warning(msg)
        self._query_errors += 1
        return []
    diff = now - row_ts
    # Valid metrics should be no more than 10 min in the future or 1h in the past
    if (diff > 3600) or (diff < -600):
        msg = 'Resource Usage stats are invalid. {}'
        if diff > 3600:
            msg = msg.format('Row timestamp is more than 1h in the past. Is `SPMA` Resource Usage Logging enabled?')
        elif diff < -600:
            msg = msg.format('Row timestamp is more than 10 min in the future. Try checking system time settings.')
        self.log.warning(msg)
        self._query_errors += 1
        return []
    return row


def tags_cleaner(self, row, query):
    column_tags = [
        {
            "stats_name": "DBC.DiskSpaceV",
            "tags": [
                {"name": "td_amp", "col": row[0]},
                {"name": "td_account", "col": row[1]},
                {"name": "td_database", "col": row[2]},
            ],
        },
        {
            "stats_name": "DBC.AllSpaceV",
            "tags": [
                {"name": "td_amp", "col": row[0]},
                {"name": "td_account", "col": row[1]},
                {"name": "td_database", "col": row[2]},
                {"name": "td_table", "col": row[3]},
            ],
        },
        {
            "stats_name": "DBC.AMPUsageV",
            "tags": [
                {"name": "td_amp", "col": row[0]},
                {"name": "td_account", "col": row[1]},
                {"name": "td_user", "col": row[2]},
            ],
        },
    ]

    for stat in column_tags:
        if stat['stats_name'] in query:
            for idx, tag in enumerate(stat['tags']):
                # tag value may be type int
                if not len(str(tag['col'])):
                    row[idx] = "undefined"
    return row
