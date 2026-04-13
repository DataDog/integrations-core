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

STORAGE_POOL_METRIC_PREFIX = 'storage_pool'

STORAGE_POOL_STATS_SIMPLE_METRICS = [
    ('capacityLimitInKb', 'capacity_limit.in_kb'),
    ('maxCapacityInKb', 'max_capacity.in_kb'),
    ('capacityInUseInKb', 'capacity.in_use_in_kb'),
    ('thickCapacityInUseInKb', 'thick_capacity.in_use_in_kb'),
    ('thinCapacityInUseInKb', 'thin_capacity.in_use_in_kb'),
    ('snapCapacityInUseInKb', 'snap_capacity.in_use_in_kb'),
    ('unreachableUnusedCapacityInKb', 'unreachable_unused_capacity.in_kb'),
    ('unusedCapacityInKb', 'unused_capacity.in_kb'),
    ('spareCapacityInKb', 'spare_capacity.in_kb'),
    ('capacityAvailableForVolumeAllocationInKb', 'capacity_available_for_volume_allocation.in_kb'),
    ('protectedCapacityInKb', 'protected_capacity.in_kb'),
    ('failedCapacityInKb', 'failed_capacity.in_kb'),
    ('inUseVacInKb', 'in_use_vac.in_kb'),
    ('backgroundScanFixedReadErrorCount', 'fixed_read_error_count'),
    ('numOfUnmappedVolumes', 'num_of_unmapped_volumes'),
    ('numOfSnapshots', 'num_of_snapshots'),
    ('numOfVolumes', 'num_of_volumes'),
    ('rfcacheReadsReceived', 'rfcache.reads_received'),
    ('rfcacheWritesReceived', 'rfcache.writes_received'),
    ('rfacheReadHit', 'rfcache.read_hit'),
    ('rfcacheReadMiss', 'rfcache.read_miss'),
    ('rfacheWriteHit', 'rfcache.write_hit'),
    ('rfcacheWriteMiss', 'rfcache.write_miss'),
    ('userDataCapacityInKb', 'user_data.capacity_in_kb'),
    ('snapshotCapacityInKb', 'snapshot.capacity_in_kb'),
    ('overallUsageRatio', 'overall_usage_ratio'),
    ('exposedCapacityInKb', 'exposed_capacity.in_kb'),
    ('ActualNetCapacityInUseInKb', 'actual_net_capacity.in_use_in_kb'),
]

STORAGE_POOL_STATS_BWC_METRICS = _COMMON_BWC_METRICS + [
    ('primaryReadBwc', 'primary_read_bwc'),
    ('primaryWriteBwc', 'primary_write_bwc'),
    ('secondaryReadBwc', 'secondary_read_bwc'),
    ('secondaryWriteBwc', 'secondary_write_bwc'),
    ('rebalanceReadBwc', 'rebalance_read_bwc'),
    ('rebalanceWriteBwc', 'rebalance_write_bwc'),
    ('totalReadBwc', 'total_read_bwc'),
    ('totalWriteBwc', 'total_write_bwc'),
    ('targetReadLatency', 'target_read_latency'),
    ('targetWriteLatency', 'target_write_latency'),
    ('fwdRebuildReadBwc', 'fwd_rebuild_read_bwc'),
    ('bckRebuildReadBwc', 'bck_rebuild_read_bwc'),
    ('normRebuildReadBwc', 'norm_rebuild_read_bwc'),
]

PROTECTION_DOMAIN_METRIC_PREFIX = 'protection_domain'

PROTECTION_DOMAIN_STATS_SIMPLE_METRICS = [
    ('exposedCapacityInKb', 'exposed_capacity.in_kb'),
    ('ActualNetCapacityInUseInKb', 'actual_net_capacity.in_use_in_kb'),
    ('capacityLimitInKb', 'capacity_limit.in_kb'),
    ('maxCapacityInKb', 'max_capacity.in_kb'),
    ('capacityInUseInKb', 'capacity.in_use_in_kb'),
    ('thickCapacityInUseInKb', 'thick_capacity.in_use_in_kb'),
    ('thinCapacityInUseInKb', 'thin_capacity.in_use_in_kb'),
    ('snapCapacityInUseInKb', 'snap_capacity.in_use_in_kb'),
    ('unreachableUnusedCapacityInKb', 'unreachable_unused_capacity.in_kb'),
    ('unusedCapacityInKb', 'unused_capacity.in_kb'),
    ('spareCapacityInKb', 'spare_capacity.in_kb'),
    ('capacityAvailableForVolumeAllocationInKb', 'capacity_available_for_volume_allocation.in_kb'),
    ('volumeAllocationLimitInKb', 'volume_allocation_limit.in_kb'),
    ('protectedCapacityInKb', 'protected_capacity.in_kb'),
    ('failedCapacityInKb', 'failed_capacity.in_kb'),
    ('inUseVacInKb', 'in_use_vac.in_kb'),
    ('backgroundScanFixedReadErrorCount', 'fixed_read_error_count'),
    ('numOfUnmappedVolumes', 'num_of_unmapped_volumes'),
    ('numOfSnapshots', 'num_of_snapshots'),
    ('rfcacheReadsReceived', 'rfcache.reads_received'),
    ('rfcacheWritesReceived', 'rfcache.writes_received'),
    ('rfacheReadHit', 'rfcache.read_hit'),
    ('rfcacheReadMiss', 'rfcache.read_miss'),
    ('rfacheWriteHit', 'rfcache.write_hit'),
    ('rfcacheWriteMiss', 'rfcache.write_miss'),
    ('netUserDataCapacityInKb', 'net_user_data_capacity.in_kb'),
    ('snapshotCapacityInKb', 'snapshot.capacity_in_kb'),
    ('overallUsageRatio', 'overall_usage_ratio'),
    ('netCapacityInUseInKb', 'net_capacity.in_use_in_kb'),
    ('rebuildWaitSendQLength', 'rebuild_wait_send_q_length'),
    ('rebalanceWaitSendQLength', 'rebalance_wait_send_q_length'),
    ('rmcacheSizeInKb', 'rmcache.size_in_kb'),
    ('rmcacheSizeInUseInKb', 'rmcache.size_in_use_in_kb'),
    ('numOfThickBaseVolumes', 'num_of_thick_base_volumes'),
    ('numOfThinBaseVolumes', 'num_of_thin_base_volumes'),
    ('numOfSds', 'num_of_sds'),
    ('numOfStoragePools', 'num_of_storage_pools'),
    ('numOfFaultSets', 'num_of_fault_sets'),
]

PROTECTION_DOMAIN_STATS_BWC_METRICS = _COMMON_BWC_METRICS + [
    ('primaryReadBwc', 'primary_read_bwc'),
    ('primaryWriteBwc', 'primary_write_bwc'),
    ('secondaryReadBwc', 'secondary_read_bwc'),
    ('secondaryWriteBwc', 'secondary_write_bwc'),
    ('rebalanceReadBwc', 'rebalance_read_bwc'),
    ('rebalanceWriteBwc', 'rebalance_write_bwc'),
    ('totalReadBwc', 'total_read_bwc'),
    ('totalWriteBwc', 'total_write_bwc'),
    ('targetReadLatency', 'target_read_latency'),
    ('targetWriteLatency', 'target_write_latency'),
    ('fwdRebuildReadBwc', 'fwd_rebuild_read_bwc'),
    ('fwdRebuildWriteBwc', 'fwd_rebuild_write_bwc'),
    ('bckRebuildReadBwc', 'bck_rebuild_read_bwc'),
    ('bckRebuildWriteBwc', 'bck_rebuild_write_bwc'),
    ('normRebuildReadBwc', 'norm_rebuild_read_bwc'),
    ('normRebuildWriteBwc', 'norm_rebuild_write_bwc'),
    ('volMigrationReadBwc', 'vol_migration_read_bwc'),
    ('volMigrationWriteBwc', 'vol_migration_write_bwc'),
]
