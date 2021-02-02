# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from itertools import chain
from typing import Callable, Iterable, List, Sequence, Union

from datadog_checks.base import AgentCheck

from ...config import is_affirmative
from ..containers import iter_unique
from .query import Query
from .transform import COLUMN_TRANSFORMERS, EXTRA_TRANSFORMERS
from .utils import SUBMISSION_METHODS, create_submission_transformer


class QueryManager(object):
    """
    This class is in charge of running any number of `Query` instances for a single Check instance.

    You will most often see it created during Check initialization like this:

    ```python
    self._query_manager = QueryManager(
        self,
        self.execute_query,
        queries=[
            queries.SomeQuery1,
            queries.SomeQuery2,
            queries.SomeQuery3,
            queries.SomeQuery4,
            queries.SomeQuery5,
        ],
        tags=self.instance.get('tags', []),
        error_handler=self._error_sanitizer,
    )
    self.check_initializations.append(self._query_manager.compile_queries)
    ```
    """

    def __init__(
        self,
        check,  # type: AgentCheck
        executor,  # type:  Callable[[str], Union[Sequence, Iterable]]
        queries=None,  # type: List[str]
        tags=None,  # type: List[str]
        error_handler=None,  # type: Callable[[str], str]
    ):  # type: (...) -> QueryManager
        """
        - **check** (_AgentCheck_) - an instance of a Check
        - **executor** (_callable_) - a callable accepting a `str` query as its sole argument and returning
          a sequence representing either the full result set or an iterator over the result set
        - **queries** (_List[Query]_) - a list of `Query` instances
        - **tags** (_List[str]_) - a list of tags to associate with every submission
        - **error_handler** (_callable_) - a callable accepting a `str` error as its sole argument and returning
          a sanitized string, useful for scrubbing potentially sensitive information libraries emit
        """
        self.check = check  # type: AgentCheck
        self.executor = executor  # type:  Callable[[str], Union[Sequence, Iterable]]
        self.tags = tags or []
        self.error_handler = error_handler
        self.queries = [Query(payload) for payload in queries or []]  # type: List[Query]
        custom_queries = list(self.check.instance.get('custom_queries', []))  # type: List[str]
        use_global_custom_queries = self.check.instance.get('use_global_custom_queries', True)  # type: str

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
        """This method compiles every `Query` object."""
        column_transformers = COLUMN_TRANSFORMERS.copy()

        for submission_method, transformer_name in SUBMISSION_METHODS.items():
            method = getattr(self.check, submission_method)
            # Save each method in the initializer -> callable format
            column_transformers[transformer_name] = create_submission_transformer(method)

        for query in self.queries:
            query.compile(column_transformers, EXTRA_TRANSFORMERS.copy())

    def execute(self, extra_tags=None):
        """This method is what you call every check run."""
        logger = self.check.log
        global_tags = list(set(self.tags + (extra_tags or [])))

        for query in self.queries:
            query_name = query.name
            query_columns = query.columns
            query_extras = query.extras
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

                sources = {}
                submission_queue = []

                tags = list(global_tags)
                tags.extend(query_tags)

                for (column_name, transformer), value in zip(query_columns, row):
                    # Columns can be ignored via configuration
                    if not column_name:
                        continue

                    sources[column_name] = value

                    column_type, transformer = transformer

                    # The transformer can be None for `source` types. Those such columns do not submit
                    # anything but are collected into the row values for other columns to reference.
                    if transformer is None:
                        continue
                    elif column_type == 'tag':
                        tags.append(transformer(None, value))
                    elif column_type == 'tag_list':
                        tags.extend(transformer(None, value))
                    else:
                        submission_queue.append((transformer, value))

                for transformer, value in submission_queue:
                    transformer(sources, value, tags=tags)

                for name, transformer in query_extras:
                    try:
                        result = transformer(sources, tags=tags)
                    except Exception as e:
                        logger.error('Error transforming %s: %s', name, e)
                        continue
                    else:
                        if result is not None:
                            sources[name] = result

    def execute_query(self, query):
        """
        Called by `execute`, this triggers query execution to check for errors immediately in a way that is compatible
        with any library. If there are no errors, this is guaranteed to return an iterator over the result set.
        """
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
