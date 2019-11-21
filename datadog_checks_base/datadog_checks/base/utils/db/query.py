# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from six import raise_from


class Query(object):
    def __init__(self, query_data):
        self.query_data = deepcopy(query_data or {})
        self.name = None
        self.query = None
        self.columns = None
        self.tags = None

    def compile(self, transformers):
        # Check for previous compilation
        if self.name is not None:
            return

        query_name = self.query_data.get('name')
        if not query_name:
            raise ValueError('query field `name` is required')
        elif not isinstance(query_name, str):
            raise ValueError('query field `name` must be a string')

        query = self.query_data.get('query')
        if not query:
            raise ValueError('field `query` for {} is required'.format(query_name))
        elif not isinstance(query, str):
            raise ValueError('field `query` for {} must be a string'.format(query_name))

        columns = self.query_data.get('columns')
        if not columns:
            raise ValueError('field `columns` for {} is required'.format(query_name))
        elif not isinstance(columns, list):
            raise ValueError('field `columns` for {} must be a list'.format(query_name))

        tags = self.query_data.get('tags', [])
        if tags is not None and not isinstance(tags, list):
            raise ValueError('field `tags` for {} must be a list'.format(query_name))

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

            column_type = column.get('type')
            if not column_type:
                raise ValueError('field `type` for column {} of {} is required'.format(column_name, query_name))
            elif not isinstance(column_type, str):
                raise ValueError('field `type` for column {} of {} must be a string'.format(column_name, query_name))
            elif column_type == 'source':
                column_data.append((column_name, (None, None)))
                continue
            elif column_type not in transformers:
                raise ValueError('unknown type `{}` for column {} of {}'.format(column_type, column_name, query_name))

            modifiers = {key: value for key, value in column.items() if key not in ('name', 'type')}

            try:
                transformer = transformers[column_type](column_name, transformers, **modifiers)
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
                if column_type == 'tag':
                    column_data.append((column_name, (column_type, transformer)))
                else:
                    # All these would actually submit data. As that is the default case, we represent it as
                    # a reference to None since if we use e.g. `value` it would never be checked anyway.
                    column_data.append((column_name, (None, transformer)))

        self.name = query_name
        self.query = query
        self.columns = tuple(column_data)
        self.tags = tags
        del self.query_data
