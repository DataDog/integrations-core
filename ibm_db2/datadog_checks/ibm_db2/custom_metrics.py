# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

import ibm_db

if TYPE_CHECKING:
    from .config_models.instance import CustomQuery
    from .connection import Db2Connection
    from .ibm_db2 import IbmDb2Check


class CustomMetricsCollector:
    def __init__(self, check: IbmDb2Check, connection: Db2Connection, custom_queries: tuple[CustomQuery, ...]):
        self._check = check
        self._connection = connection
        self._custom_queries = custom_queries

    def query_custom(self):
        for custom_query in self._custom_queries:
            metric_prefix = custom_query.metric_prefix
            if not metric_prefix:  # no cov
                self._check.log.error('Custom query field `metric_prefix` is required')
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.query
            if not query:  # no cov
                self._check.log.error('Custom query field `query` is required for metric_prefix `%s`', metric_prefix)
                continue

            columns = custom_query.columns
            if not columns:  # no cov
                self._check.log.error('Custom query field `columns` is required for metric_prefix `%s`', metric_prefix)
                continue

            rows = self._connection.iter_rows(query, ibm_db.fetch_tuple)
            self._check.log.debug('Running query for metric_prefix `%s`: `%s`', metric_prefix, query)

            # Trigger query execution
            try:
                first_row = next(rows)
            except Exception as e:  # no cov
                self._check.log.error('Error executing query for metric_prefix `%s`: `%s`', metric_prefix, e)
                continue

            for row in chain((first_row,), rows):
                if not row:  # no cov
                    self._check.log.debug(
                        'Query result for metric_prefix `%s`: returned an empty result', metric_prefix
                    )
                    continue

                if len(columns) != len(row):  # no cov
                    self._check.log.error(
                        'Query result for metric_prefix `%s`: expected %s columns, got %s',
                        metric_prefix,
                        len(columns),
                        len(row),
                    )
                    continue

                metric_info = []
                query_tags = list(self._check.tags)
                query_tags.extend(custom_query.tags or ())

                for column, value in zip(columns, row):
                    # Columns can be ignored via configuration.
                    if not column:  # no cov
                        continue

                    name = column.get('name')
                    if not name:  # no cov
                        self._check.log.error('Column field `name` is required for metric_prefix `%s`', metric_prefix)
                        break

                    column_type = column.get('type')
                    if not column_type:  # no cov
                        self._check.log.error(
                            'Column field `type` is required for column `%s` of metric_prefix `%s`',
                            name,
                            metric_prefix,
                        )
                        break

                    if column_type == 'tag':
                        query_tags.append('{}:{}'.format(name, value))
                    else:
                        if not hasattr(self._check, column_type):
                            self._check.log.error(
                                'Invalid submission method `%s` for metric column `%s` of metric_prefix `%s`',
                                column_type,
                                name,
                                metric_prefix,
                            )
                            break
                        try:
                            metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                        except (ValueError, TypeError):  # no cov
                            self._check.log.error(
                                'Non-numeric value `%s` for metric column `%s` of metric_prefix `%s`',
                                value,
                                name,
                                metric_prefix,
                            )
                            break

                # Only submit metrics if there were absolutely no errors - all or nothing.
                else:
                    for info in metric_info:
                        metric, value, method = info
                        getattr(self._check, method)(metric, value, tags=query_tags)
