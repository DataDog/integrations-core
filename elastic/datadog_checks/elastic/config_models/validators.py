# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers


def initialize_instance(values, **kwargs):
    if 'custom_queries' in values:
        custom_queries = values['custom_queries']
        for custom_query in custom_queries:
            # Each custom query must have `endpoint`, `data_path`, and 'columns`
            if not (custom_query.get('endpoint') and custom_query.get('data_path') and custom_query.get('columns')):
                raise ValueError('Each custom query must have an `endpoint`, `data_path`, and `columns` values')

            columns = custom_query.get('columns')
            for column in columns:
                # Each query must have both `name` and `value_path`
                if not (column.get('value_path') and column.get('name')):
                    raise ValueError('Each column must have a `value_path` and `name` values')
                if column.get('type', 'gauge') not in ['gauge', 'monotonic_count', 'rate', 'tag']:
                    raise ValueError(
                        'Metric type {} not recognized for custom query {}'.format(column.get('type'), column)
                    )

    return values
