# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

SYSTEM_METRIC_PREFIX = 'system'

SYSTEM_MDM_CLUSTER_SIMPLE_METRICS = [
    ('goodNodesNum', 'mdm_cluster.good_nodes'),
    ('goodReplicasNum', 'mdm_cluster.good_replicas'),
]

SYSTEM_MDM_CLUSTER_STATE_METRICS = [
    ('clusterState', 'mdm_cluster.cluster_state', 'cluster_state'),
    ('clusterMode', 'mdm_mode', 'mdm_mode'),
]

SYSTEM_STATS_SIMPLE_METRICS = [
    ('capacityInUseInKb', 'capacity.in_use_in_kb'),
    ('maxCapacityInKb', 'max_capacity.in_kb'),
    ('thickCapacityInUseInKb', 'thick_capacity.in_use_in_kb'),
    ('thinCapacityInUseInKb', 'thin_capacity.in_use_in_kb'),
    ('snapCapacityInUseInKb', 'snap_capacity.in_use_in_kb'),
    ('unusedCapacityInKb', 'unused_capacity.in_kb'),
    ('spareCapacityInKb', 'spare_capacity.in_kb'),
    ('backgroundScanFixedReadErrorCount', 'fixed_read_error_count'),
    ('rmcacheSizeInKb', 'rmcache.size_in_kb'),
    ('rmcacheSizeInUseInKb', 'rmcache.size_in_use_in_kb'),
    ('numOfUnmappedVolumes', 'num_of_unmapped_volumes'),
    ('numOfMappedToAllVolumes', 'num_of_mapped_to_all_volumes'),
    ('numOfSnapshots', 'num_of_snapshots'),
    ('rfcacheReadsReceived', 'rfcache.reads_received'),
    ('rfcacheWritesReceived', 'rfcache.writes_received'),
    ('rfacheReadHit', 'rfcache.read_hit'),
    ('rfcacheReadMiss', 'rfcache.read_miss'),
    ('rfacheWriteHit', 'rfcache.write_hit'),
    ('rfcacheWriteMiss', 'rfcache.write_miss'),
    ('userDataCapacityInKb', 'user_data.capacity_in_kb'),
    ('snapshotCapacityInKb', 'snapshot.capacity_in_kb'),
    ('overallUsageRatio', 'overall_usage_ratio'),
    ('numSdsReconnections', 'num_sds_reconnections'),
    ('numDevErrors', 'num_dev_errors'),
    ('numSdsSdrDisconnections', 'num_sds_sdr_disconnections'),
    ('numSdrSdcDisconnections', 'num_sdr_sdc_disconnections'),
]

BWC_SUB_FIELDS = [
    ('numSeconds', 'num_seconds'),
    ('totalWeightInKb', 'total_weight_in_kb'),
    ('numOccured', 'num_occured'),
]

_COMMON_BWC_METRICS = [
    ('userDataReadBwc', 'user_data_read_bwc'),
    ('userDataWriteBwc', 'user_data_write_bwc'),
    ('userDataTrimBwc', 'user_data_trim_bwc'),
    ('userDataSdcReadLatency', 'user_data_sdc_read_latency'),
    ('userDataSdcWriteLatency', 'user_data_sdc_write_latency'),
    ('userDataSdcTrimLatency', 'user_data_sdc_trim_latency'),
]

SYSTEM_STATS_BWC_METRICS = _COMMON_BWC_METRICS + [
    ('journalerReadLatency', 'journaler_read_latency'),
    ('journalerWriteLatency', 'journaler_write_latency'),
    ('targetWriteLatency', 'target_write_latency'),
]

VOLUME_METRIC_PREFIX = 'volume'

VOLUME_STATS_SIMPLE_METRICS = [
    ('numOfChildVolumes', 'num_of_child_volumes'),
    ('numOfMappedSdcs', 'num_of_mapped_sdcs'),
    ('rplTotalJournalCap', 'rpl_total_journal_cap'),
    ('rplUsedJournalCap', 'rpl_used_journal_cap'),
]

VOLUME_STATS_BWC_METRICS = list(_COMMON_BWC_METRICS)
