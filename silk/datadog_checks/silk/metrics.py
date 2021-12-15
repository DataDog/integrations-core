# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class Metric(object):
    """
    Metric object contains"
        - the metric sub prefix,
        - metrics mapping (response JSON key to metric name and metric type)
        - tags mapping (response JSON key to tag name)
    """

    def __init__(self, prefix, metrics, tags=None):
        self.prefix = prefix
        for key, name_method in metrics.items():
            if isinstance(name_method, tuple):
                continue
            else:
                metrics[key] = (name_method, 'gauge')

        self.metrics = metrics
        self.tags = tags if tags else {}


METRICS = {
    'hosts': Metric(
        **{
            'prefix': 'system',
            'metrics': {'views_count': 'views_count', 'volumes_count': 'volumes_count'},
        }
    ),
    'volumes': Metric(
        **{
            'prefix': 'volume',
            'metrics': {
                'avg_compressed_ratio': 'compressed_ratio.avg',
                'logical_capacity': 'logical_capacity',
                'no_dedup': 'no_dedup',
                'size': 'size',
                'snapshots_logical_capacity': 'snapshots_logical_capacity',
                'stream_avg_compressed_size_in_bytes': 'stream_average_compressed_bytes',
            },
            'tags': {
                'iscsi_tgt_converted_name': 'volume_name',
                'name': 'volume_raw_name',
                # node_id, might be context explosion
            },
        }
    ),
    'stats/system': Metric(
        **{
            'prefix': 'stats.system',
            'metrics': {
                'iops_avg': 'io_ops.avg',
                'iops_max': 'io_ops.max',
                'latency_inner': 'latency.inner',
                'latency_outer': 'latency.outer',
                'resolution': 'resolution',
                'throughput_avg': 'throughput.avg',
                'throughput_max': 'throughput.max',
            },
        }
    ),
    'stats/volumes': Metric(
        **{
            'prefix': 'stats.volume',
            'metrics': {
                'iops_avg': ('io_ops.avg', 'gauge'),
                'iops_max': 'io_ops.max',
                'latency_inner': 'latency.inner',
                'latency_outer': 'latency.outer',
                'resolution': 'resolution',
                'throughput_avg': 'throughput.avg',
                'throughput_max': 'throughput.max',
            },
            'tags': {
                'peer_k2_name': 'peer_name',
                'volume_name': 'volume_name',
            },
        }
    ),
    'system/capacity': Metric(
        **{
            'prefix': 'system.capacity',
            'metrics': {
                'allocated': 'allocated',
                'allocated_snapshots_and_views': 'allocated_snapshots_and_views',
                'allocated_volumes': 'allocated_volumes',
                'curr_dt_chunk': 'curr_dt_chunk',
                'free': 'free',
                'logical': 'logical',
                'physical': 'physical',
                'provisioned': 'provisioned',
                'provisioned_snapshots': 'provisioned_snapshots',
                'provisioned_views': 'provisioned_views',
                'provisioned_volumes': 'provisioned_volumes',
                'reserved': 'reserved',
                'total': 'total',
            },
            'tags': {
                'state': 'capacity_state',
            },
        }
    ),
}
