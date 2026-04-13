# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

SYSTEM_MDM_CLUSTER_METRICS = [
    {'name': 'dell_powerflex.system.mdm_cluster.good_nodes', 'value': 3},
    {'name': 'dell_powerflex.system.mdm_cluster.good_replicas', 'value': 2},
    {
        'name': 'dell_powerflex.system.mdm_cluster.cluster_state',
        'value': 1,
        'extra_tags': ['cluster_state:ClusteredNormal'],
    },
    {'name': 'dell_powerflex.system.mdm_mode', 'value': 1, 'extra_tags': ['mdm_mode:ThreeNodes']},
]

SYSTEM_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.system.capacity.in_use_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.system.max_capacity.in_kb', 'value': 311270400},
    {'name': 'dell_powerflex.system.thick_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.system.thin_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.system.snap_capacity.in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.system.unused_capacity.in_kb', 'value': 179488768},
    {'name': 'dell_powerflex.system.spare_capacity.in_kb', 'value': 130733056},
    {'name': 'dell_powerflex.system.fixed_read_error_count', 'value': 0},
    {'name': 'dell_powerflex.system.rmcache.size_in_kb', 'value': 393216},
    {'name': 'dell_powerflex.system.rmcache.size_in_use_in_kb', 'value': 0},
    {'name': 'dell_powerflex.system.num_of_unmapped_volumes', 'value': 2},
    {'name': 'dell_powerflex.system.num_of_mapped_to_all_volumes', 'value': 0},
    {'name': 'dell_powerflex.system.num_of_snapshots', 'value': 2},
    {'name': 'dell_powerflex.system.rfcache.reads_received', 'value': 0},
    {'name': 'dell_powerflex.system.rfcache.writes_received', 'value': 0},
    {'name': 'dell_powerflex.system.rfcache.read_hit', 'value': 0},
    {'name': 'dell_powerflex.system.rfcache.read_miss', 'value': 0},
    {'name': 'dell_powerflex.system.rfcache.write_hit', 'value': 0},
    {'name': 'dell_powerflex.system.rfcache.write_miss', 'value': 0},
    {'name': 'dell_powerflex.system.user_data.capacity_in_kb', 'value': 1048576},
    {'name': 'dell_powerflex.system.snapshot.capacity_in_kb', 'value': 0},
    {'name': 'dell_powerflex.system.overall_usage_ratio', 'value': 96.0},
    {'name': 'dell_powerflex.system.num_sds_reconnections', 'value': 8},
    {'name': 'dell_powerflex.system.num_dev_errors', 'value': 0},
    {'name': 'dell_powerflex.system.num_sds_sdr_disconnections', 'value': 0},
    {'name': 'dell_powerflex.system.num_sdr_sdc_disconnections', 'value': 0},
]

VOLUME_STATS_SIMPLE_METRICS = [
    {'name': 'dell_powerflex.volume.num_of_child_volumes', 'value': 1},
    {'name': 'dell_powerflex.volume.num_of_mapped_sdcs', 'value': 1},
    {'name': 'dell_powerflex.volume.rpl_total_journal_cap', 'value': 0},
    {'name': 'dell_powerflex.volume.rpl_used_journal_cap', 'value': 0},
]

VOLUME_STATS_BWC_METRICS = [
    'dell_powerflex.volume.user_data_read_bwc',
    'dell_powerflex.volume.user_data_write_bwc',
    'dell_powerflex.volume.user_data_trim_bwc',
    'dell_powerflex.volume.user_data_sdc_read_latency',
    'dell_powerflex.volume.user_data_sdc_write_latency',
    'dell_powerflex.volume.user_data_sdc_trim_latency',
]

SYSTEM_STATS_BWC_METRICS = [
    'dell_powerflex.system.user_data_read_bwc',
    'dell_powerflex.system.user_data_write_bwc',
    'dell_powerflex.system.user_data_trim_bwc',
    'dell_powerflex.system.user_data_sdc_read_latency',
    'dell_powerflex.system.user_data_sdc_write_latency',
    'dell_powerflex.system.user_data_sdc_trim_latency',
    'dell_powerflex.system.journaler_read_latency',
    'dell_powerflex.system.journaler_write_latency',
    'dell_powerflex.system.target_write_latency',
]
