# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'custom_queries' in values:
        custom_queries = values['custom_queries']
        for custom_query in custom_queries:
            # Each custom query must have `endpoint`, `path`, and 'columns`
            if not (custom_query.get('endpoint') and custom_query.get('path') and custom_query.get('columns')):
                raise ValueError('Each custom query must have an `endpoint`, `path`, and `columns` values')

            columns = custom_query.get('columns')
            for column in columns:
                # Each query must have both `dd_name` and `es_name`
                if not (column.get('es_name') and column.get('dd_name')):
                    raise ValueError('Each column must have a `es_name` and `dd_name` values')

    return values
