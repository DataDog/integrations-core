# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from itertools import chain
from typing import Any, Callable, Dict, List, Tuple  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.utils.db.types import QueriesExecutor, QueriesSubmitter, Transformer  # noqa: F401

from ...config import is_affirmative
from ..containers import iter_unique
from .query import Query
from .transform import COLUMN_TRANSFORMERS, EXTRA_TRANSFORMERS
from .utils import SUBMISSION_METHODS, create_submission_transformer, tracked_query


class QueryExecutor(object):
    """
    QueryExecutor is a lower-level implementation of QueryManager which supports multiple instances
    per AgentCheck. It is used to execute queries via the `executor` parameter and submit resulting
    telemetry via the `submitter` parameter.
    """

    def __init__(
        self,
        executor,  # type: QueriesExecutor
        submitter,  # type: QueriesSubmitter
        queries=None,  # type: List[Dict[str, Any]]
        tags=None,  # type: List[str]
        error_handler=None,  # type: Callable[[str], str]
        hostname=None,  # type: str
        logger=None,
        track_operation_time=False,  # type: bool
    ):  # type: (...) -> QueryExecutor
        self.executor = executor  # type: QueriesExecutor
        self.submitter = submitter  # type: QueriesSubmitter
        for submission_method in SUBMISSION_METHODS.keys():
            if not hasattr(self.submitter, submission_method):
                raise ValueError(
                    'QueryExecutor submitter is missing required submission method `{}`'.format(submission_method)
                )

        self.tags = tags or []
        self.error_handler = error_handler
        self.queries = [Query(payload) for payload in queries or []]  # type: List[Query]
        self.hostname = hostname  # type: str
        self.logger = logger or logging.getLogger(__name__)
        self.track_operation_time = track_operation_time

    def compile_queries(self):
        """This method compiles every `Query` object."""
        column_transformers = COLUMN_TRANSFORMERS.copy()  # type: Dict[str, Transformer]

        for submission_method, transformer_name in SUBMISSION_METHODS.items():
            method = getattr(self.submitter, submission_method)
            # Save each method in the initializer -> callable format
            column_transformers[transformer_name] = create_submission_transformer(method)

        for query in self.queries:
            query.compile(column_transformers, EXTRA_TRANSFORMERS.copy())

    def execute(self, extra_tags=None):
        """This method executes all of the compiled queries."""

        global_tags = list(self.tags)
        if extra_tags:
            global_tags.extend(list(extra_tags))

        for query in self.queries:
            if not query.should_execute():
                self.logger.debug(
                    'Query %s was executed less than %s seconds ago, skipping',
                    query.name,
                    query.collection_interval,
                )
                continue

            query_name = query.name
            query_columns = query.column_transformers
            extra_transformers = query.extra_transformers
            query_tags = query.base_tags

            try:
                if self.track_operation_time:
                    with tracked_query(check=self.submitter, operation=query_name):
                        rows = self.execute_query(query.query)
                else:
                    rows = self.execute_query(query.query)
            except Exception as e:
                if self.error_handler:
                    self.logger.error('Error querying %s: %s', query_name, self.error_handler(str(e)))
                else:
                    self.logger.error('Error querying %s: %s', query_name, e)

                continue

            for row in rows:
                if not self._is_row_valid(query, row):
                    continue

                # It holds the query results
                sources = {}  # type: Dict[str, str]
                # It holds the transformers defined in query_columns along with the column value
                submission_queue = []  # type: List[Tuple[Transformer, Any]]
                tags = global_tags + query_tags

                for (column_name, type_transformer), column_value in zip(query_columns, row):
                    # Columns can be ignored via configuration
                    if not column_name:
                        continue

                    sources[column_name] = column_value
                    column_type, transformer = type_transformer

                    # The transformer can be None for `source` types. Those such columns do not submit
                    # anything but are collected into the row values for other columns to reference.
                    if transformer is None:
                        continue
                    elif column_type == 'tag':
                        tags.append(transformer(None, column_value))  # get_tag transformer
                    elif column_type == 'tag_not_null':
                        if column_value is not None:
                            tags.append(transformer(None, column_value))  # get_tag transformer
                    elif column_type == 'tag_list':
                        tags.extend(transformer(None, column_value))  # get_tag_list transformer
                    else:
                        submission_queue.append((transformer, column_value))

                for transformer, value in submission_queue:
                    transformer(sources, value, tags=tags, hostname=self.hostname, raw=query.metric_name_raw)

                for name, transformer in extra_transformers:
                    try:
                        result = transformer(sources, tags=tags, hostname=self.hostname, raw=query.metric_name_raw)
                    except Exception as e:
                        self.logger.error('Error transforming %s: %s', name, e)
                        continue
                    else:
                        if result is not None:
                            sources[name] = result

    def _is_row_valid(self, query, row):
        # type: (Query, List) -> bool
        if not row:
            self.logger.debug('Query %s returned an empty result', query.name)
            return False

        num_columns = len(query.column_transformers)
        if num_columns != len(row):
            self.logger.error(
                'Query %s expected %d column%s, got %d',
                query.name,
                num_columns,
                's' if num_columns > 1 else '',
                len(row),
            )
            return False
        return True

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


class QueryManager(QueryExecutor):
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

    Note: This class is not in charge of opening or closing connections, just running queries.
    """

    def __init__(
        self,
        check,  # type: AgentCheck
        executor,  # type:  QueriesExecutor
        queries=None,  # type: List[Dict[str, Any]]
        tags=None,  # type: List[str]
        error_handler=None,  # type: Callable[[str], str]
        hostname=None,  # type: str
    ):  # type: (...) -> QueryManager
        """
        - **check** (_AgentCheck_) - an instance of a Check
        - **executor** (_callable_) - a callable accepting a `str` query as its sole argument and returning
          a sequence representing either the full result set or an iterator over the result set
        - **queries** (_List[Dict]_) - a list of queries in dict format
        - **tags** (_List[str]_) - a list of tags to associate with every submission
        - **error_handler** (_callable_) - a callable accepting a `str` error as its sole argument and returning
          a sanitized string, useful for scrubbing potentially sensitive information libraries emit
        """
        super(QueryManager, self).__init__(
            executor=executor,
            submitter=check,
            queries=queries,
            tags=tags,
            error_handler=error_handler,
            hostname=hostname,
            logger=check.log,
        )
        self.check = check  # type: AgentCheck

        only_custom_queries = is_affirmative(self.check.instance.get('only_custom_queries', False))  # type: bool
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

        # Override statement queries if only running custom queries
        if only_custom_queries:
            self.queries = []

        # Deduplicate
        for i, custom_query in enumerate(iter_unique(custom_queries), 1):
            query = Query(custom_query)
            query.query_data.setdefault('name', 'custom query #{}'.format(i))
            self.queries.append(query)

        if len(self.queries) == 0:
            self.logger.warning('QueryManager initialized with no query')

    def execute(self, extra_tags=None):
        # This needs to stay here b/c when we construct a QueryManager in a check's __init__
        # there is no check ID at that point
        self.logger = self.check.log

        return super(QueryManager, self).execute(extra_tags)
