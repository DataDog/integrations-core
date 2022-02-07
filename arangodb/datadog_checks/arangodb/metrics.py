# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRIC_MAP = {
    # 'rocksdb_engine_throttle_bps': 'rocksdb.engine.throttle.bps',
    'arangodb_client_connection_statistics_connection_time': 'client.connection.statistics.connection.time'
    # TODO: Continue adding more metrics
}


def construct_metrics_config(metric_map, type_overrides):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith('_total'):
            raw_metric_name = raw_metric_name[:-6]
            metric_name = metric_name[:-6]
        elif metric_name.endswith('.count'):
            metric_name = metric_name[:-6]

        config = {raw_metric_name: {'name': metric_name}}
        if raw_metric_name in type_overrides:
            config[raw_metric_name]['type'] = type_overrides[raw_metric_name]

        metrics.append(config)

    return metrics
