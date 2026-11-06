# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

SYSTEM_MDM_CLUSTER_METRICS: list[dict[str, Any]] = [
    {'name': 'dell_powerflex.mdm_cluster.good_nodes', 'value': 3},
    {'name': 'dell_powerflex.mdm_cluster.good_replicas', 'value': 2},
    {
        'name': 'dell_powerflex.mdm_cluster.cluster_state',
        'value': 1,
        'extra_tags': ['cluster_state:ClusteredNormal'],
    },
    {'name': 'dell_powerflex.mdm_mode', 'value': 1, 'extra_tags': ['mdm_mode:ThreeNodes']},
]

SYSTEM_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 179488768},
    {'name': 'dell_powerflex.spare_capacity.in_kb', 'value': 130733056},
    {'name': 'dell_powerflex.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.rmcache.size_in_kb', 'value': 393216},
    {'name': 'dell_powerflex.rmcache.size_in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.num_of_unmapped_volumes', 'value': 2},
    {'name': 'dell_powerflex.num_of_mapped_to_all_volumes', 'value': 0},
    {'name': 'dell_powerflex.num_of_snapshots', 'value': 2},
    {'name': 'dell_powerflex.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.user_data.capacity_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.overall_usage_ratio', 'value': 96.0},
    {'name': 'dell_powerflex.num_sds_reconnections', 'value': 8},
    {'name': 'dell_powerflex.num_dev_errors', 'value': 0},
    {'name': 'dell_powerflex.num_sds_sdr_disconnections', 'value': 0},
    {'name': 'dell_powerflex.num_sdr_sdc_disconnections', 'value': 0},
]

VOLUME_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.num_of_child_volumes', 'value': 1},
    {'name': 'dell_powerflex.num_of_mapped_sdcs', 'value': 1},
    {'name': 'dell_powerflex.rpl_total_journal_cap', 'value': 0},
    {'name': 'dell_powerflex.rpl_used_journal_cap', 'value': 0},
]

VOLUME_STATS_BWC_METRICS = [
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_trim_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
    'dell_powerflex.user_data_sdc_trim_latency',
]

STORAGE_POOL_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.capacity_limit.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.unreachable_unused_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 179488768},
    {'name': 'dell_powerflex.spare_capacity.in_kb', 'value': 130733056},
    {'name': 'dell_powerflex.capacity_available_for_volume_allocation.in_kb', 'value': 75497472},
    {'name': 'dell_powerflex.protected_capacity.in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.failed_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.in_use_vac.in_kb', 'value': 67108864},
    {'name': 'dell_powerflex.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.num_of_unmapped_volumes', 'value': 2},
    {'name': 'dell_powerflex.num_of_snapshots', 'value': 2},
    {'name': 'dell_powerflex.num_of_volumes', 'value': 4},
    {'name': 'dell_powerflex.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.user_data.capacity_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.overall_usage_ratio', 'value': 96.0},
    {'name': 'dell_powerflex.exposed_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.actual_net_capacity.in_use_in_kb', 'value': 0},
]

STORAGE_POOL_STATS_BWC_METRICS = [
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_trim_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
    'dell_powerflex.user_data_sdc_trim_latency',
    'dell_powerflex.primary_read_bwc',
    'dell_powerflex.primary_write_bwc',
    'dell_powerflex.secondary_read_bwc',
    'dell_powerflex.secondary_write_bwc',
    'dell_powerflex.rebalance_read_bwc',
    'dell_powerflex.rebalance_write_bwc',
    'dell_powerflex.total_read_bwc',
    'dell_powerflex.total_write_bwc',
    'dell_powerflex.target_read_latency',
    'dell_powerflex.target_write_latency',
    'dell_powerflex.fwd_rebuild_read_bwc',
    'dell_powerflex.fwd_rebuild_write_bwc',
    'dell_powerflex.bck_rebuild_read_bwc',
    'dell_powerflex.bck_rebuild_write_bwc',
    'dell_powerflex.norm_rebuild_read_bwc',
    'dell_powerflex.norm_rebuild_write_bwc',
]

PROTECTION_DOMAIN_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.capacity_limit.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.unreachable_unused_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 179488768},
    {'name': 'dell_powerflex.spare_capacity.in_kb', 'value': 130733056},
    {'name': 'dell_powerflex.capacity_available_for_volume_allocation.in_kb', 'value': 75497472},
    {'name': 'dell_powerflex.volume_allocation_limit.in_kb', 'value': 864026624},
    {'name': 'dell_powerflex.protected_capacity.in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.failed_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.in_use_vac.in_kb', 'value': 67108864},
    {'name': 'dell_powerflex.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.num_of_unmapped_volumes', 'value': 2},
    {'name': 'dell_powerflex.num_of_snapshots', 'value': 2},
    {'name': 'dell_powerflex.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.net_user_data_capacity.in_kb', 'value': 524288},
    {'name': 'dell_powerflex.user_data.capacity_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.overall_usage_ratio', 'value': 96.0},
    {'name': 'dell_powerflex.net_capacity.in_use_in_kb', 'value': 524288},
    {'name': 'dell_powerflex.rebuild_wait_send_q_length', 'value': 0},
    {'name': 'dell_powerflex.rebalance_wait_send_q_length', 'value': 0},
    {'name': 'dell_powerflex.rmcache.size_in_kb', 'value': 393216},
    {'name': 'dell_powerflex.rmcache.size_in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.num_of_thick_base_volumes', 'value': 0},
    {'name': 'dell_powerflex.num_of_thin_base_volumes', 'value': 2},
    {'name': 'dell_powerflex.num_of_sds', 'value': 3},
    {'name': 'dell_powerflex.num_of_storage_pools', 'value': 2},
    {'name': 'dell_powerflex.num_of_fault_sets', 'value': 0},
    {'name': 'dell_powerflex.exposed_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.actual_net_capacity.in_use_in_kb', 'value': 0},
]

PROTECTION_DOMAIN_STATS_BWC_METRICS = [
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_trim_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
    'dell_powerflex.user_data_sdc_trim_latency',
    'dell_powerflex.primary_read_bwc',
    'dell_powerflex.primary_write_bwc',
    'dell_powerflex.secondary_read_bwc',
    'dell_powerflex.secondary_write_bwc',
    'dell_powerflex.rebalance_read_bwc',
    'dell_powerflex.rebalance_write_bwc',
    'dell_powerflex.total_read_bwc',
    'dell_powerflex.total_write_bwc',
    'dell_powerflex.target_read_latency',
    'dell_powerflex.target_write_latency',
    'dell_powerflex.fwd_rebuild_read_bwc',
    'dell_powerflex.fwd_rebuild_write_bwc',
    'dell_powerflex.bck_rebuild_read_bwc',
    'dell_powerflex.bck_rebuild_write_bwc',
    'dell_powerflex.norm_rebuild_read_bwc',
    'dell_powerflex.norm_rebuild_write_bwc',
    'dell_powerflex.vol_migration_read_bwc',
    'dell_powerflex.vol_migration_write_bwc',
]

SDS_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.capacity_limit.in_kb', 'value': 103756800},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 103756800},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 349184},
    {'name': 'dell_powerflex.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.unreachable_unused_capacity.in_kb', 'value': 0},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 103407616},
    {'name': 'dell_powerflex.failed_vac.in_kb', 'value': 0},
    {'name': 'dell_powerflex.in_use_vac.in_kb', 'value': 22380544},
    {'name': 'dell_powerflex.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.num_of_devices', 'value': 1},
    {'name': 'dell_powerflex.compression_ratio', 'value': 1.0},
    {'name': 'dell_powerflex.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.reads_pending', 'value': 0},
    {'name': 'dell_powerflex.rfcache.io_errors', 'value': 0},
    {'name': 'dell_powerflex.user_data.capacity_in_kb', 'value': 349184},
    {'name': 'dell_powerflex.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.rmcache.size_in_kb', 'value': 131072},
    {'name': 'dell_powerflex.rmcache.size_in_use_in_kb', 'value': 0},
]

SDS_STATS_BWC_METRICS = [
    'dell_powerflex.primary_read_bwc',
    'dell_powerflex.primary_write_bwc',
    'dell_powerflex.secondary_read_bwc',
    'dell_powerflex.secondary_write_bwc',
    'dell_powerflex.total_read_bwc',
    'dell_powerflex.total_write_bwc',
    'dell_powerflex.vol_migration_read_bwc',
    'dell_powerflex.vol_migration_write_bwc',
    'dell_powerflex.target_read_latency',
    'dell_powerflex.target_write_latency',
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
]

DEVICE_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.avg_read_size_in_bytes', 'value': 353621},
    {'name': 'dell_powerflex.avg_write_size_in_bytes', 'value': 0},
    {'name': 'dell_powerflex.avg_read_latency_in_microsec', 'value': 9596},
    {'name': 'dell_powerflex.avg_write_latency_in_microsec', 'value': 0},
    {'name': 'dell_powerflex.capacity_limit.in_kb', 'value': 103756800},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 103756800},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 349184},
    {'name': 'dell_powerflex.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.failed_vac.in_kb', 'value': 0},
    {'name': 'dell_powerflex.in_use_vac.in_kb', 'value': 22380544},
    {'name': 'dell_powerflex.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.user_data.capacity_in_kb', 'value': 349184},
    {'name': 'dell_powerflex.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.compression_ratio', 'value': 1.0},
    {'name': 'dell_powerflex.inaccessible_capacity.in_kb', 'value': 0},
]

DEVICE_ONLY_METRICS = [
    'dell_powerflex.avg_read_size_in_bytes',
    'dell_powerflex.avg_write_size_in_bytes',
    'dell_powerflex.avg_read_latency_in_microsec',
    'dell_powerflex.avg_write_latency_in_microsec',
    'dell_powerflex.inaccessible_capacity.in_kb',
]

DEVICE_STATS_BWC_METRICS = [
    'dell_powerflex.primary_read_bwc',
    'dell_powerflex.primary_write_bwc',
    'dell_powerflex.secondary_read_bwc',
    'dell_powerflex.secondary_write_bwc',
    'dell_powerflex.total_read_bwc',
    'dell_powerflex.total_write_bwc',
    'dell_powerflex.target_read_latency',
    'dell_powerflex.target_write_latency',
]

SDC_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.num_of_mapped_volumes', 'value': 2},
]

SDC_STATS_BWC_METRICS = [
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_trim_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
    'dell_powerflex.user_data_sdc_trim_latency',
]

SYSTEM_STATS_BWC_METRICS = [
    'dell_powerflex.user_data_read_bwc',
    'dell_powerflex.user_data_write_bwc',
    'dell_powerflex.user_data_trim_bwc',
    'dell_powerflex.user_data_sdc_read_latency',
    'dell_powerflex.user_data_sdc_write_latency',
    'dell_powerflex.user_data_sdc_trim_latency',
    'dell_powerflex.primary_read_bwc',
    'dell_powerflex.primary_write_bwc',
    'dell_powerflex.secondary_read_bwc',
    'dell_powerflex.secondary_write_bwc',
    'dell_powerflex.total_read_bwc',
    'dell_powerflex.total_write_bwc',
    'dell_powerflex.target_read_latency',
    'dell_powerflex.target_write_latency',
    'dell_powerflex.journaler_read_latency',
    'dell_powerflex.journaler_write_latency',
]

BWC_SUFFIXES = ['num_seconds', 'total_weight_in_kb', 'num_occured']


DEFAULT_GATEWAY_URL = 'https://localhost:443'
BASE_TAGS = [f'powerflex_gateway_url:{DEFAULT_GATEWAY_URL}']

# E2E expected metric points (excludes the dynamic powerflex_gateway_url tag).
# The test prepends that tag before asserting.

SYSTEM_TAGS = ['system_id:1fcf40fc60c6520f', 'dell_type:system']
POOL1_TAGS = [
    'storage_pool_id:25155ba600000000',
    'storage_pool_name:pool1',
    'protection_domain_id:68c139ee00000000',
    'dell_type:storage_pool',
]
POOL2_TAGS = [
    'storage_pool_id:2515d0d600000001',
    'storage_pool_name:storagepool2',
    'protection_domain_id:68c139ee00000000',
    'dell_type:storage_pool',
]
PD_TAGS = [
    'protection_domain_id:68c139ee00000000',
    'protection_domain_name:domain1',
    'system_id:1fcf40fc60c6520f',
    'dell_type:protection_domain',
]
SDS3_TAGS = [
    'sds_id:d1c062b700000000',
    'sds_name:SDS3',
    'protection_domain_id:68c139ee00000000',
    'fault_set_id:faultset00000001',
    'dell_type:sds',
]
SDS2_TAGS = ['sds_id:d1c062b800000001', 'sds_name:SDS2', 'protection_domain_id:68c139ee00000000', 'dell_type:sds']
SDS1_TAGS = ['sds_id:d1c062b900000002', 'sds_name:SDS1', 'protection_domain_id:68c139ee00000000', 'dell_type:sds']
SDC1_TAGS = [
    'sdc_id:1b8659fd00000001',
    'sdc_guid:33FC0AF2-5180-45D8-9BDC-8E2F78CD60BF',
    'sdc_type:AppSdc',
    'sdc_ip:10.0.1.250',
    'peer_mdm_id:mdm00000001',
    'dell_type:sdc',
]
SDC2_TAGS = [
    'sdc_id:1b8659fc00000000',
    'sdc_guid:BE3BC972-269A-4931-96B8-286BFA45C004',
    'sdc_type:AppSdc',
    'sdc_ip:10.0.1.223',
    'dell_type:sdc',
]
SDC3_TAGS = [
    'sdc_id:1b8659fe00000002',
    'sdc_guid:46EE0B53-B823-4E68-B0B4-41A2DEC5A425',
    'sdc_type:AppSdc',
    'sdc_ip:10.0.1.228',
    'dell_type:sdc',
]
VOL_VOLUMEE_TAGS = [
    'volume_id:c58b06e700000000',
    'volume_name:volumee',
    'volume_type:ThinProvisioned',
    'storage_pool_id:25155ba600000000',
    'dell_type:volume',
]
VOL_BIGVOLUME_TAGS = [
    'volume_id:c58b06e800000001',
    'volume_name:bigvolume',
    'volume_type:ThinProvisioned',
    'storage_pool_id:25155ba600000000',
    'dell_type:volume',
]
VOL_SNAP1_TAGS = [
    'volume_id:c58b06e900000002',
    'volume_name:volumee-snap-01',
    'volume_type:Snapshot',
    'storage_pool_id:25155ba600000000',
    'ancestor_volume_id:c58b06e700000000',
    'dell_type:volume',
]
VOL_SNAP2_TAGS = [
    'volume_id:c58b06ea00000003',
    'volume_name:volumee-snap-02',
    'volume_type:Snapshot',
    'storage_pool_id:25155ba600000000',
    'ancestor_volume_id:c58b06e900000002',
    'dell_type:volume',
]
DEV1_TAGS = [
    'device_id:f7fd7d0b00020000',
    'device_name:sds1-dev1',
    'current_path_name:/dev/sdb',
    'storage_pool_id:25155ba600000000',
    'sds_id:d1c062b900000002',
    'dell_type:device',
]
DEV2_TAGS = [
    'device_id:f7fd7d0a00010000',
    'device_name:sds2-dev1',
    'current_path_name:/dev/sdb',
    'storage_pool_id:25155ba600000000',
    'sds_id:d1c062b800000001',
    'dell_type:device',
]
DEV3_TAGS = [
    'device_id:f7f77d0900000000',
    'device_name:sds3-dev1',
    'current_path_name:/dev/sdb',
    'storage_pool_id:25155ba600000000',
    'sds_id:d1c062b700000000',
    'dell_type:device',
]

ALL_EXPECTED_METRICS: list[dict] = [
    # ---- system ----
    {'name': 'dell_powerflex.system.count', 'value': 1, 'tags': SYSTEM_TAGS},
    *[
        {'name': m['name'], 'value': m['value'], 'tags': SYSTEM_TAGS + m.get('extra_tags', [])}
        for m in SYSTEM_MDM_CLUSTER_METRICS + SYSTEM_STATS_SIMPLE_METRICS
    ],
    *[
        {
            'name': f'{p}.{s}',
            'value': 42 if p == 'dell_powerflex.user_data_read_bwc' and s == 'num_occured' else 0,
            'tags': SYSTEM_TAGS,
        }
        for p in SYSTEM_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    # ---- storage_pool: pool1 ----
    {'name': 'dell_powerflex.storage_pool.count', 'value': 1, 'tags': POOL1_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': POOL1_TAGS} for m in STORAGE_POOL_STATS_SIMPLE_METRICS],
    *[
        {'name': f'{p}.{s}', 'value': 0, 'tags': POOL1_TAGS}
        for p in STORAGE_POOL_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    # ---- storage_pool: storagepool2 ----
    {'name': 'dell_powerflex.storage_pool.count', 'value': 1, 'tags': POOL2_TAGS},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 0, 'tags': POOL2_TAGS},
    {'name': 'dell_powerflex.max_capacity.in_kb', 'value': 0, 'tags': POOL2_TAGS},
    {'name': 'dell_powerflex.num_of_volumes', 'value': 0, 'tags': POOL2_TAGS},
    *[
        {'name': f'{p}.{s}', 'value': 0, 'tags': POOL2_TAGS}
        for p in STORAGE_POOL_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    # ---- protection_domain: domain1 ----
    {'name': 'dell_powerflex.protection_domain.count', 'value': 1, 'tags': PD_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': PD_TAGS} for m in PROTECTION_DOMAIN_STATS_SIMPLE_METRICS],
    *[
        {'name': f'{p}.{s}', 'value': 0, 'tags': PD_TAGS}
        for p in PROTECTION_DOMAIN_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    # ---- sds: SDS3 ----
    {'name': 'dell_powerflex.sds.count', 'value': 1, 'tags': SDS3_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': SDS3_TAGS} for m in SDS_STATS_SIMPLE_METRICS],
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDS3_TAGS} for p in SDS_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- sds: SDS2 ----
    {'name': 'dell_powerflex.sds.count', 'value': 1, 'tags': SDS2_TAGS},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 350208, 'tags': SDS2_TAGS},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 103406592, 'tags': SDS2_TAGS},
    {'name': 'dell_powerflex.num_of_devices', 'value': 1, 'tags': SDS2_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDS2_TAGS} for p in SDS_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- sds: SDS1 ----
    {'name': 'dell_powerflex.sds.count', 'value': 1, 'tags': SDS1_TAGS},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 349184, 'tags': SDS1_TAGS},
    {'name': 'dell_powerflex.unused_capacity.in_kb', 'value': 103407616, 'tags': SDS1_TAGS},
    {'name': 'dell_powerflex.num_of_devices', 'value': 1, 'tags': SDS1_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDS1_TAGS} for p in SDS_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- sdc: SDC1 ----
    {'name': 'dell_powerflex.sdc.count', 'value': 1, 'tags': SDC1_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': SDC1_TAGS} for m in SDC_STATS_SIMPLE_METRICS],
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDC1_TAGS} for p in SDC_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- sdc: SDC2 ----
    {'name': 'dell_powerflex.sdc.count', 'value': 1, 'tags': SDC2_TAGS},
    {'name': 'dell_powerflex.num_of_mapped_volumes', 'value': 0, 'tags': SDC2_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDC2_TAGS} for p in SDC_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- sdc: SDC3 ----
    {'name': 'dell_powerflex.sdc.count', 'value': 1, 'tags': SDC3_TAGS},
    {'name': 'dell_powerflex.num_of_mapped_volumes', 'value': 0, 'tags': SDC3_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': SDC3_TAGS} for p in SDC_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- volume: volumee ----
    {'name': 'dell_powerflex.volume.count', 'value': 1, 'tags': VOL_VOLUMEE_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': VOL_VOLUMEE_TAGS} for m in VOLUME_STATS_SIMPLE_METRICS],
    *[
        {'name': f'{p}.{s}', 'value': 0, 'tags': VOL_VOLUMEE_TAGS}
        for p in VOLUME_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    {'name': 'dell_powerflex.volume.sdc_mapping', 'value': 1, 'tags': VOL_VOLUMEE_TAGS + ['sdc_id:1b8659fd00000001']},
    # ---- volume: bigvolume ----
    {'name': 'dell_powerflex.volume.count', 'value': 1, 'tags': VOL_BIGVOLUME_TAGS},
    {'name': 'dell_powerflex.num_of_child_volumes', 'value': 0, 'tags': VOL_BIGVOLUME_TAGS},
    {'name': 'dell_powerflex.num_of_mapped_sdcs', 'value': 1, 'tags': VOL_BIGVOLUME_TAGS},
    *[
        {'name': f'{p}.{s}', 'value': 0, 'tags': VOL_BIGVOLUME_TAGS}
        for p in VOLUME_STATS_BWC_METRICS
        for s in BWC_SUFFIXES
    ],
    {'name': 'dell_powerflex.volume.sdc_mapping', 'value': 1, 'tags': VOL_BIGVOLUME_TAGS + ['sdc_id:1b8659fd00000001']},
    # ---- volume: volumee-snap-01 ----
    {'name': 'dell_powerflex.volume.count', 'value': 1, 'tags': VOL_SNAP1_TAGS},
    {'name': 'dell_powerflex.num_of_child_volumes', 'value': 1, 'tags': VOL_SNAP1_TAGS},
    {'name': 'dell_powerflex.num_of_mapped_sdcs', 'value': 0, 'tags': VOL_SNAP1_TAGS},
    # ---- volume: volumee-snap-02 ----
    {'name': 'dell_powerflex.volume.count', 'value': 1, 'tags': VOL_SNAP2_TAGS},
    {'name': 'dell_powerflex.num_of_child_volumes', 'value': 0, 'tags': VOL_SNAP2_TAGS},
    {'name': 'dell_powerflex.num_of_mapped_sdcs', 'value': 0, 'tags': VOL_SNAP2_TAGS},
    # ---- device: sds1-dev1 ----
    {'name': 'dell_powerflex.device.count', 'value': 1, 'tags': DEV1_TAGS},
    *[{'name': m['name'], 'value': m['value'], 'tags': DEV1_TAGS} for m in DEVICE_STATS_SIMPLE_METRICS],
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': DEV1_TAGS} for p in DEVICE_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- device: sds2-dev1 ----
    {'name': 'dell_powerflex.device.count', 'value': 1, 'tags': DEV2_TAGS},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 350208, 'tags': DEV2_TAGS},
    {'name': 'dell_powerflex.avg_read_latency_in_microsec', 'value': 12793, 'tags': DEV2_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': DEV2_TAGS} for p in DEVICE_STATS_BWC_METRICS for s in BWC_SUFFIXES],
    # ---- device: sds3-dev1 ----
    {'name': 'dell_powerflex.device.count', 'value': 1, 'tags': DEV3_TAGS},
    {'name': 'dell_powerflex.capacity.in_use_in_kb', 'value': 349184, 'tags': DEV3_TAGS},
    {'name': 'dell_powerflex.avg_read_latency_in_microsec', 'value': 10023, 'tags': DEV3_TAGS},
    *[{'name': f'{p}.{s}', 'value': 0, 'tags': DEV3_TAGS} for p in DEVICE_STATS_BWC_METRICS for s in BWC_SUFFIXES],
]
