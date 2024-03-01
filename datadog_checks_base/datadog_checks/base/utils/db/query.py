# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from typing import Any, Dict, List, Tuple  # noqa: F401

from six import raise_from

from datadog_checks.base.utils.db.types import Transformer, TransformerFactory  # noqa: F401
from datadog_checks.base.utils.time import get_timestamp

from .utils import create_extra_transformer


class Query(object):
    """
    This class accepts a single `dict` argument which is necessary to run the query. The representation
    is based on our `custom_queries` format originally designed and implemented in !1528.

    It is now part of all our database integrations and
    [other](https://cloud.google.com/solutions/sap/docs/sap-hana-monitoring-agent-planning-guide#defining_custom_queries)
    products have since adopted this format.
    """

    def __init__(self, query_data):
        '''
        Parameters:
            query_data (Dict[str, Any]): The query data to run the query. It should contain the following fields:
                - name (str): The name of the query.
                - query (str): The query to run.
                - columns (List[Dict[str, Any]]): Each column should contain the following fields:
                    - name (str): The name of the column.
                    - type (str): The type of the column.
                    - (Optional) Any other field that the column transformer for the type requires.
                - (Optional) extras (List[Dict[str, Any]]): Each extra transformer should contain the following fields:
                    - name (str): The name of the extra transformer.
                    - type (str): The type of the extra transformer.
                    - (Optional) Any other field that the extra transformer for the type requires.
                - (Optional) tags (List[str]): The tags to add to the query result.
                - (Optional) collection_interval (int): The collection interval (in seconds) of the query.
                    Note:
                        If collection_interval is None, the query will be run every check run.
                        If the collection interval is less than check collection interval,
                        the query will be run every check run.
                        If the collection interval is greater than check collection interval,
                        the query will NOT BE RUN exactly at the collection interval.
                        The query will be run at the next check run after the collection interval has passed.
                - (Optional) metric_prefix (str): The prefix to add to the metric name.
                    Note: If the metric prefix is None, the default metric prefix `<INTEGRATION>.` will be used.
        '''
        # Contains the data to fill the rest of the attributes
        self.query_data = deepcopy(query_data or {})  # type: Dict[str, Any]
        self.name = None  # type: str
        # The actual query
        self.query = None  # type: str
        # Contains a mapping of column_name -> column_type, transformer
        self.column_transformers = None  # type: Tuple[Tuple[str, Tuple[str, Transformer]]]
        # These transformers are used to collect extra metrics calculated from the query result
        self.extra_transformers = None  # type: List[Tuple[str, Transformer]]
        # Contains the tags defined in query_data, more tags can be added later from the query result
        self.base_tags = None  # type: List[str]
        # The collecton interval (in seconds) of the query. If None, the query will be run every check run.
        self.collection_interval = None  # type: int
        # The last time the query was executed. If None, the query has never been executed.
        # This is only used when the collection_interval is not None.
        self.__last_execution_time = None  # type: float
        # whether to ignore any defined namespace prefix. True when `metric_prefix` is defined.
        self.metric_name_raw = False  # type: bool

    def compile(
        self,
        column_transformers,  # type: Dict[str, TransformerFactory]
        extra_transformers,  # type: Dict[str, TransformerFactory]
    ):
        # type: (...) -> None

        """
        This idempotent method will be called by `QueryManager.compile_queries` so you
        should never need to call it directly.
        """
        # Check for previous compilation
        if self.name is not None:
            return

        query_name = self.query_data.get('name')
        if not query_name:
            raise ValueError('query field `name` is required')
        elif not isinstance(query_name, str):
            raise ValueError('query field `name` must be a string')

        metric_prefix = self.query_data.get('metric_prefix')
        if metric_prefix is not None:
            if not isinstance(metric_prefix, str):
                raise ValueError('field `metric_prefix` for {} must be a string'.format(query_name))
            elif not metric_prefix:
                raise ValueError('field `metric_prefix` for {} must not be empty'.format(query_name))

        query = self.query_data.get('query')
        if not query:
            raise ValueError('field `query` for {} is required'.format(query_name))
        elif query_name.startswith('custom query #') and not isinstance(query, str):
            raise ValueError('field `query` for {} must be a string'.format(query_name))

        columns = self.query_data.get('columns')
        if not columns:
            raise ValueError('field `columns` for {} is required'.format(query_name))
        elif not isinstance(columns, list):
            raise ValueError('field `columns` for {} must be a list'.format(query_name))

        tags = self.query_data.get('tags', [])
        if tags is not None and not isinstance(tags, list):
            raise ValueError('field `tags` for {} must be a list'.format(query_name))

        # Keep track of all defined names
        sources = {}

        column_data = []
        for i, column in enumerate(columns, 1):
            # Columns can be ignored via configuration.
            if not column:
                column_data.append((None, None))
                continue
            elif not isinstance(column, dict):
                raise ValueError('column #{} of {} is not a mapping'.format(i, query_name))

            column_name = column.get('name')
            if not column_name:
                raise ValueError('field `name` for column #{} of {} is required'.format(i, query_name))
            elif not isinstance(column_name, str):
                raise ValueError('field `name` for column #{} of {} must be a string'.format(i, query_name))
            elif column_name in sources:
                raise ValueError(
                    'the name {} of {} was already defined in {} #{}'.format(
                        column_name, query_name, sources[column_name]['type'], sources[column_name]['index']
                    )
                )

            sources[column_name] = {'type': 'column', 'index': i}

            column_type = column.get('type')
            if not column_type:
                raise ValueError('field `type` for column {} of {} is required'.format(column_name, query_name))
            elif not isinstance(column_type, str):
                raise ValueError('field `type` for column {} of {} must be a string'.format(column_name, query_name))
            elif column_type == 'source':
                column_data.append((column_name, (None, None)))
                continue
            elif column_type not in column_transformers:
                raise ValueError('unknown type `{}` for column {} of {}'.format(column_type, column_name, query_name))

            __column_type_is_tag = column_type in ('tag', 'tag_list', 'tag_not_null')
            modifiers = {key: value for key, value in column.items() if key not in ('name', 'type')}

            try:
                if not __column_type_is_tag and metric_prefix:
                    # if metric_prefix is defined, we prepend it to the column name
                    column_name = "{}.{}".format(metric_prefix, column_name)
                transformer = column_transformers[column_type](column_transformers, column_name, **modifiers)
            except Exception as e:
                error = 'error compiling type `{}` for column {} of {}: {}'.format(
                    column_type, column_name, query_name, e
                )

                # Prepend helpful error text.
                #
                # When an exception is raised in the context of another one, both will be printed. To avoid
                # this we set the context to None. https://www.python.org/dev/peps/pep-0409/
                raise_from(type(e)(error), None)
            else:
                if __column_type_is_tag:
                    column_data.append((column_name, (column_type, transformer)))
                else:
                    # All these would actually submit data. As that is the default case, we represent it as
                    # a reference to None since if we use e.g. `value` it would never be checked anyway.
                    column_data.append((column_name, (None, transformer)))

        submission_transformers = column_transformers.copy()  # type: Dict[str, Transformer]
        submission_transformers.pop('tag')
        submission_transformers.pop('tag_list')
        submission_transformers.pop('tag_not_null')

        extras = self.query_data.get('extras', [])  # type: List[Dict[str, Any]]
        if not isinstance(extras, list):
            raise ValueError('field `extras` for {} must be a list'.format(query_name))

        extra_data = []  # type: List[Tuple[str, Transformer]]
        for i, extra in enumerate(extras, 1):
            if not isinstance(extra, dict):
                raise ValueError('extra #{} of {} is not a mapping'.format(i, query_name))

            extra_name = extra.get('name')  # type: str
            if not extra_name:
                raise ValueError('field `name` for extra #{} of {} is required'.format(i, query_name))
            elif not isinstance(extra_name, str):
                raise ValueError('field `name` for extra #{} of {} must be a string'.format(i, query_name))
            elif extra_name in sources:
                raise ValueError(
                    'the name {} of {} was already defined in {} #{}'.format(
                        extra_name, query_name, sources[extra_name]['type'], sources[extra_name]['index']
                    )
                )

            sources[extra_name] = {'type': 'extra', 'index': i}

            extra_type = extra.get('type')  # type: str  # Is the key in a transformers dict
            if not extra_type:
                if 'expression' in extra:
                    extra_type = 'expression'
                else:
                    raise ValueError('field `type` for extra {} of {} is required'.format(extra_name, query_name))
            elif not isinstance(extra_type, str):
                raise ValueError('field `type` for extra {} of {} must be a string'.format(extra_name, query_name))
            elif extra_type not in extra_transformers and extra_type not in submission_transformers:
                raise ValueError('unknown type `{}` for extra {} of {}'.format(extra_type, extra_name, query_name))

            transformer_factory = extra_transformers.get(
                extra_type, submission_transformers.get(extra_type)
            )  # type: TransformerFactory

            extra_source = extra.get('source')
            if extra_type in submission_transformers:
                if not extra_source:
                    raise ValueError('field `source` for extra {} of {} is required'.format(extra_name, query_name))

                modifiers = {key: value for key, value in extra.items() if key not in ('name', 'type', 'source')}
            else:
                modifiers = {key: value for key, value in extra.items() if key not in ('name', 'type')}
                modifiers['sources'] = sources

            try:
                transformer = transformer_factory(submission_transformers, extra_name, **modifiers)
            except Exception as e:
                error = 'error compiling type `{}` for extra {} of {}: {}'.format(extra_type, extra_name, query_name, e)

                raise_from(type(e)(error), None)
            else:
                if extra_type in submission_transformers:
                    transformer = create_extra_transformer(transformer, extra_source)

                extra_data.append((extra_name, transformer))

        collection_interval = self.query_data.get('collection_interval')
        if collection_interval is not None:
            if not isinstance(collection_interval, (int, float)):
                raise ValueError('field `collection_interval` for {} must be a number'.format(query_name))
            elif int(collection_interval) <= 0:
                raise ValueError(
                    'field `collection_interval` for {} must be a positive number after rounding'.format(query_name)
                )
            collection_interval = int(collection_interval)

        self.name = query_name
        self.query = query
        self.column_transformers = tuple(column_data)
        self.extra_transformers = tuple(extra_data)
        self.base_tags = tags
        self.collection_interval = collection_interval
        self.metric_name_raw = metric_prefix is not None
        del self.query_data

    def should_execute(self):
        '''
        Check if the query should be executed based on the collection interval.

        :return: True if the query should be executed, False otherwise.
        '''
        if self.collection_interval is None:
            # if the collection interval is None, the query should always be executed.
            return True

        now = get_timestamp()
        if self.__last_execution_time is None or now - self.__last_execution_time >= self.collection_interval:
            # if the last execution time is None (the query has never been executed),
            # if the time since the last execution is greater than or equal to the collection interval,
            # the query should be executed.
            self.__last_execution_time = now
            return True

        return False
