# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'custom_queries' in values:
        custom_queries = values['custom_queries']
        for custom_query in custom_queries:
            # Each custom query must have `endpoint` and `queries`
            if not (custom_query.get('endpoint') and custom_query.get('metrics')):
                raise ValueError('Each custom query must have an `endpoint` and `metrics` value')

            metrics = custom_query.get('metrics')
            for metric in metrics:
                # Each query must have both `datadog_metric_name` and `es_metric_name`
                if not (metric.get('datadog_metric_name') and metric.get('es_metric_name')):
                    raise ValueError('Each custom query must have a `datadog_metric_name` and `es_metric_name` value')

    return values
