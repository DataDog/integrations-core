# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import chain

from ...config import is_affirmative
from ..containers import iter_unique
from .query import Query
from .transform import TRANSFORMERS
from .utils import SUBMISSION_METHODS, create_submission_transformer


class QueryManager(object):
    def __init__(self, check, executor, queries=None, tags=None, error_handler=None):
        self.check = check
        self.executor = executor
        self.queries = queries or []
        self.tags = tags or []
        self.error_handler = error_handler

        custom_queries = list(self.check.instance.get('custom_queries', []))
        use_global_custom_queries = self.check.instance.get('use_global_custom_queries', True)

        # Handle overrides
        if use_global_custom_queries == 'extend':
            custom_queries.extend(self.check.init_config.get('global_custom_queries', []))
        elif (
            not custom_queries
            and 'global_custom_queries' in self.check.init_config
            and is_affirmative(use_global_custom_queries)
        ):
            custom_queries = self.check.init_config.get('global_custom_queries', [])

        # Deduplicate
        for i, custom_query in enumerate(iter_unique(custom_queries), 1):
            query = Query(custom_query)
            query.query_data.setdefault('name', 'custom query #{}'.format(i))
            self.queries.append(query)

    def compile_queries(self):
        transformers = TRANSFORMERS.copy()

        for submission_method in SUBMISSION_METHODS:
            method = getattr(self.check, submission_method)
            # Save each method in the initializer -> callable format
            transformers[submission_method] = create_submission_transformer(method)

        for query in self.queries:
            query.compile(transformers)

    def execute(self):
        logger = self.check.log
        global_tags = self.tags

        for query in self.queries:
            query_name = query.name
            query_columns = query.columns
            query_tags = query.tags
            num_columns = len(query_columns)

            try:
                rows = self.execute_query(query.query)
            except Exception as e:
                if self.error_handler:
                    logger.error('Error querying %s: %s', query_name, self.error_handler(str(e)))
                else:
                    logger.error('Error querying %s: %s', query_name, e)

                continue

            for row in rows:
                if not row:
                    logger.debug('Query %s returned an empty result', query_name)
                    continue

                if num_columns != len(row):
                    logger.error(
                        'Query %s expected %d column%s, got %d',
                        query_name,
                        num_columns,
                        's' if num_columns > 1 else '',
                        len(row),
                    )
                    continue

                row_values = {}
                submission_queue = []

                tags = list(global_tags)
                tags.extend(query_tags)

                for (column_name, transformer), value in zip(query_columns, row):
                    # Columns can be ignored via configuration
                    if not column_name:
                        continue

                    row_values[column_name] = value

                    column_type, transformer = transformer

                    # The transformer can be None for `source` types. Those such columns do not submit
                    # anything but are collected into the row values for other columns to reference.
                    if transformer is None:
                        continue
                    elif column_type == 'tag':
                        tags.append(transformer(value, None))
                    else:
                        submission_queue.append((transformer, value))

                for transformer, value in submission_queue:
                    transformer(value, row_values, tags=tags)

    def execute_query(self, query):
        rows = self.executor(query)
        if rows is None:
            return iter([])
        else:
            rows = iter(rows)

        # Ensure we trigger query execution
        try:
            first_row = next(rows)
        except StopIteration:
            return iter([])

        return chain((first_row,), rows)
