# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
Lustre filesystem metrics definitions for testing.

This module contains metric name constants used in tests to validate
the Lustre integration's metric collection capabilities.
"""


def _expand_metric_base(base_metrics, suffixes):
    """Expand base metric names with statistical suffixes."""
    expanded = []
    for base in base_metrics:
        for suffix in suffixes:
            expanded.append(f"{base}.{suffix}")
    return expanded


# Statistical suffixes for histogram metrics
HISTOGRAM_SUFFIXES = ['count', 'min', 'max', 'sum']
EXTENDED_HISTOGRAM_SUFFIXES = ['count', 'min', 'max', 'sum', 'sumsq']

# Core device metrics (no suffixes)
DEVICE_METRICS = [
    'lustre.device.health',
    'lustre.device.refcount',
]

# Basic LNet statistics (no suffixes)
LNET_STATS_METRICS = [
    'lustre.net.msgs_alloc',
    'lustre.net.msgs_max',
    'lustre.net.rst_alloc',
    'lustre.net.errors',
    'lustre.net.send_count',
    'lustre.net.resend_count',
    'lustre.net.response_timeout_count',
    'lustre.net.local_interrupt_count',
    'lustre.net.local_dropped_count',
    'lustre.net.local_aborted_count',
    'lustre.net.local_no_route_count',
    'lustre.net.local_timeout_count',
    'lustre.net.local_error_count',
    'lustre.net.remote_dropped_count',
    'lustre.net.remote_error_count',
    'lustre.net.remote_timeout_count',
    'lustre.net.network_timeout_count',
    'lustre.net.recv_count',
    'lustre.net.route_count',
    'lustre.net.drop_count',
    'lustre.net.send_length',
    'lustre.net.recv_length',
    'lustre.net.route_length',
    'lustre.net.drop_length',
]

# LNet local node metrics (no suffixes)
LNET_LOCAL_METRICS = [
    'lustre.net.local.status',
    'lustre.net.local.statistics.send_count',
    'lustre.net.local.statistics.recv_count',
    'lustre.net.local.statistics.drop_count',
    'lustre.net.local.sent_stats.put',
    'lustre.net.local.sent_stats.get',
    'lustre.net.local.sent_stats.reply',
    'lustre.net.local.sent_stats.ack',
    'lustre.net.local.sent_stats.hello',
    'lustre.net.local.received_stats.put',
    'lustre.net.local.received_stats.get',
    'lustre.net.local.received_stats.reply',
    'lustre.net.local.received_stats.ack',
    'lustre.net.local.received_stats.hello',
    'lustre.net.local.dropped_stats.put',
    'lustre.net.local.dropped_stats.get',
    'lustre.net.local.dropped_stats.reply',
    'lustre.net.local.dropped_stats.ack',
    'lustre.net.local.dropped_stats.hello',
    'lustre.net.local.health_stats.fatal_error',
    'lustre.net.local.health_stats.health_value',
    'lustre.net.local.health_stats.interrupts',
    'lustre.net.local.health_stats.dropped',
    'lustre.net.local.health_stats.aborted',
    'lustre.net.local.health_stats.no_route',
    'lustre.net.local.health_stats.timeouts',
    'lustre.net.local.health_stats.error',
    'lustre.net.local.health_stats.ping_count',
    'lustre.net.local.health_stats.next_ping',
    'lustre.net.local.tunables.peer_timeout',
    'lustre.net.local.tunables.peer_credits',
    'lustre.net.local.tunables.peer_buffer_credits',
    'lustre.net.local.tunables.credits',
    'lustre.net.local.lnd_tunables.conns_per_peer',
    'lustre.net.local.lnd_tunables.timeout',
    'lustre.net.local.lnd_tunables.tos',
]

# LNet peer metrics (no suffixes)
LNET_PEER_METRICS = [
    'lustre.net.peer.statistics.send_count',
    'lustre.net.peer.statistics.recv_count',
    'lustre.net.peer.statistics.drop_count',
    'lustre.net.peer.sent_stats.put',
    'lustre.net.peer.sent_stats.get',
    'lustre.net.peer.sent_stats.reply',
    'lustre.net.peer.sent_stats.ack',
    'lustre.net.peer.sent_stats.hello',
    'lustre.net.peer.received_stats.put',
    'lustre.net.peer.received_stats.get',
    'lustre.net.peer.received_stats.reply',
    'lustre.net.peer.received_stats.ack',
    'lustre.net.peer.received_stats.hello',
    'lustre.net.peer.dropped_stats.put',
    'lustre.net.peer.dropped_stats.get',
    'lustre.net.peer.dropped_stats.reply',
    'lustre.net.peer.dropped_stats.ack',
    'lustre.net.peer.dropped_stats.hello',
    'lustre.net.peer.health_stats.health_value',
    'lustre.net.peer.health_stats.dropped',
    'lustre.net.peer.health_stats.timeout',
    'lustre.net.peer.health_stats.error',
    'lustre.net.peer.health_stats.network_timeout',
    'lustre.net.peer.health_stats.ping_count',
    'lustre.net.peer.health_stats.next_ping',
]

# LDLM namespace pool base metrics
LDLM_NAMESPACE_POOL_BASE = [
    'lustre.ldlm.namespaces.pool.granted',
    'lustre.ldlm.namespaces.pool.grant_rate',
    'lustre.ldlm.namespaces.pool.cancel_rate',
    'lustre.ldlm.namespaces.pool.grant_plan',
    'lustre.ldlm.namespaces.pool.slv',
    'lustre.ldlm.namespaces.pool.recalc_freed',
    'lustre.ldlm.namespaces.pool.recalc_timing',
]

# LDLM service base metrics
LDLM_SERVICE_BASE = [
    'lustre.ldlm.services.req_waittime',
    'lustre.ldlm.services.req_qdepth',
    'lustre.ldlm.services.req_active',
    'lustre.ldlm.services.req_timeout',
    'lustre.ldlm.services.reqbuf_avail',
    'lustre.ldlm.services.ldlm_cancel',
    'lustre.ldlm.services.ldlm_bl_callback',
]

# Expand LDLM metrics with appropriate suffixes
LDLM_NAMESPACE_POOL_METRICS = _expand_metric_base(LDLM_NAMESPACE_POOL_BASE, HISTOGRAM_SUFFIXES)
LDLM_SERVICE_METRICS = _expand_metric_base(LDLM_SERVICE_BASE, EXTENDED_HISTOGRAM_SUFFIXES)

# Common metrics across all Lustre configurations
COMMON_METRICS = (
    DEVICE_METRICS
    + LNET_STATS_METRICS
    + LNET_LOCAL_METRICS
    + LNET_PEER_METRICS
    + LDLM_NAMESPACE_POOL_METRICS
    + LDLM_SERVICE_METRICS
)

# Client filesystem configuration metrics (no suffixes)
FILESYSTEM_CONFIG_METRICS = [
    'lustre.filesystem.file_heat',
    'lustre.filesystem.enable_setstripe_gid',
    'lustre.filesystem.max_read_ahead_whole_mb',
    'lustre.filesystem.max_read_ahead_per_file_mb',
    'lustre.filesystem.blocksize',
    'lustre.filesystem.intent_mkdir',
    'lustre.filesystem.enable_statahead_fname',
    'lustre.filesystem.inode_cache',
    'lustre.filesystem.filename_enc_use_old_base64',
    'lustre.filesystem.checksum_pages',
    'lustre.filesystem.statahead_max',
    'lustre.filesystem.statahead_agl',
    'lustre.filesystem.max_easize',
    'lustre.filesystem.hybrid_io_read_threshold_bytes',
    'lustre.filesystem.max_read_ahead_mb',
    'lustre.filesystem.enable_filename_encryption',
    'lustre.filesystem.kbytesfree',
    'lustre.filesystem.default_easize',
    'lustre.filesystem.kbytesavail',
    'lustre.filesystem.filestotal',
    'lustre.filesystem.filesfree',
    'lustre.filesystem.kbytestotal',
    'lustre.filesystem.lazystatfs',
    'lustre.filesystem.fast_read',
    'lustre.filesystem.hybrid_io_write_threshold_bytes',
]

# OSC (Object Storage Client) base metrics
OSC_BASE = [
    'lustre.osc.req_waittime',
    'lustre.osc.req_active',
    'lustre.osc.ldlm_glimpse_enqueue',
    'lustre.osc.ldlm_extent_enqueue',
    'lustre.osc.read_bytes',
    'lustre.osc.write_bytes',
    'lustre.osc.ost_setattr',
    'lustre.osc.ost_read',
    'lustre.osc.ost_write',
    'lustre.osc.ost_connect',
    'lustre.osc.ost_disconnect',
    'lustre.osc.ost_punch',
    'lustre.osc.ost_statfs',
    'lustre.osc.ost_sync',
    'lustre.osc.ldlm_cancel',
    'lustre.osc.obd_ping',
]

# MDC (Metadata Client) base metrics
MDC_BASE = [
    'lustre.mdc.req_waittime',
    'lustre.mdc.req_active',
    'lustre.mdc.ldlm_ibits_enqueue',
    'lustre.mdc.ost_set_info',
    'lustre.mdc.mds_getattr',
    'lustre.mdc.mds_getattr_lock',
    'lustre.mdc.mds_close',
    'lustre.mdc.mds_readpage',
    'lustre.mdc.mds_connect',
    'lustre.mdc.mds_get_root',
    'lustre.mdc.mds_statfs',
    'lustre.mdc.mds_sync',
    'lustre.mdc.mds_getxattr',
    'lustre.mdc.mds_hsm_state_set',
    'lustre.mdc.ldlm_cancel',
    'lustre.mdc.obd_ping',
    'lustre.mdc.llog_origin_handle_open',
    'lustre.mdc.llog_origin_handle_next_block',
    'lustre.mdc.llog_origin_handle_read_header',
    'lustre.mdc.seq_query',
]

# Filesystem operation base metrics
FILESYSTEM_OPERATION_BASE = [
    'lustre.filesystem.read_bytes',
    'lustre.filesystem.write_bytes',
    'lustre.filesystem.read',
    'lustre.filesystem.write',
    'lustre.filesystem.open',
    'lustre.filesystem.close',
    'lustre.filesystem.seek',
    'lustre.filesystem.fsync',
    'lustre.filesystem.readdir',
    'lustre.filesystem.setattr',
    'lustre.filesystem.truncate',
    'lustre.filesystem.getattr',
    'lustre.filesystem.unlink',
    'lustre.filesystem.mkdir',
    'lustre.filesystem.rmdir',
    'lustre.filesystem.mknod',
    'lustre.filesystem.rename',
    'lustre.filesystem.setxattr',
    'lustre.filesystem.getxattr',
    'lustre.filesystem.inode_permission',
    'lustre.filesystem.opencount',
    'lustre.filesystem.openclosetime',
]

# Special filesystem metrics (count only)
FILESYSTEM_COUNT_ONLY_METRICS = [
    'lustre.filesystem.ioctl.count',
]

# Expand client metrics with appropriate suffixes
OSC_METRICS = _expand_metric_base(OSC_BASE, EXTENDED_HISTOGRAM_SUFFIXES)
MDC_METRICS = _expand_metric_base(MDC_BASE, EXTENDED_HISTOGRAM_SUFFIXES)
FILESYSTEM_OPERATION_METRICS = _expand_metric_base(FILESYSTEM_OPERATION_BASE, EXTENDED_HISTOGRAM_SUFFIXES)

# Client metrics - combination of all client-side metrics
CLIENT_METRICS = (
    FILESYSTEM_CONFIG_METRICS + OSC_METRICS + MDC_METRICS + FILESYSTEM_OPERATION_METRICS + FILESYSTEM_COUNT_ONLY_METRICS
)

# MDS export base metrics
MDS_EXPORT_BASE = [
    'lustre.mds.mdt.exports.open',
    'lustre.mds.mdt.exports.close',
    'lustre.mds.mdt.exports.mknod',
    'lustre.mds.mdt.exports.unlink',
    'lustre.mds.mdt.exports.mkdir',
    'lustre.mds.mdt.exports.rmdir',
    'lustre.mds.mdt.exports.rename',
    'lustre.mds.mdt.exports.getattr',
    'lustre.mds.mdt.exports.setattr',
    'lustre.mds.mdt.exports.getxattr',
    'lustre.mds.mdt.exports.setxattr',
    'lustre.mds.mdt.exports.statfs',
    'lustre.mds.mdt.exports.sync',
    'lustre.mds.mdt.exports.samedir_rename',
    'lustre.mds.mdt.exports.parallel_rename_file',
    'lustre.mds.mdt.exports.crossdir_rename',
]

# MDS service base metrics
MDS_SERVICE_BASE = [
    'lustre.mds.mdt.req_waittime',
    'lustre.mds.mdt.req_qdepth',
    'lustre.mds.mdt.req_active',
    'lustre.mds.mdt.req_timeout',
    'lustre.mds.mdt.reqbuf_avail',
    'lustre.mds.mdt.ldlm_ibits_enqueue',
    'lustre.mds.mdt.mds_reint_setattr',
    'lustre.mds.mdt.mds_reint_create',
    'lustre.mds.mdt.mds_reint_unlink',
    'lustre.mds.mdt.mds_reint_open',
    'lustre.mds.mdt.mds_reint_setxattr',
    'lustre.mds.mdt.ost_set_info',
    'lustre.mds.mdt.mds_getattr_lock',
    'lustre.mds.mdt.mds_connect',
    'lustre.mds.mdt.mds_get_root',
    'lustre.mds.mdt.mds_statfs',
    'lustre.mds.mdt.mds_sync',
    'lustre.mds.mdt.mds_hsm_state_set',
    'lustre.mds.mdt.obd_ping',
    'lustre.mds.mdt.llog_origin_handle_open',
    'lustre.mds.mdt.llog_origin_handle_next_block',
    'lustre.mds.mdt.llog_origin_handle_read_header',
]

# MGS count-only metrics
MGS_COUNT_ONLY_METRICS = [
    'lustre.mgs.exports.tgtreg.count',
]

# OSD (Object Storage Device) configuration metrics (no suffixes)
OSD_CONFIG_METRICS = [
    'lustre.osd.kbytesfree',
    'lustre.osd.blocksize',
    'lustre.osd.filesfree',
    'lustre.osd.filestotal',
    'lustre.osd.kbytesavail',
    'lustre.osd.kbytestotal',
]

# Expand MDS metrics with appropriate suffixes
MDS_EXPORT_METRICS = _expand_metric_base(MDS_EXPORT_BASE, EXTENDED_HISTOGRAM_SUFFIXES)
MDS_SERVICE_METRICS = _expand_metric_base(MDS_SERVICE_BASE, EXTENDED_HISTOGRAM_SUFFIXES)

# MDS metrics - combination of all MDS-side metrics
MDS_METRICS = MDS_EXPORT_METRICS + MDS_SERVICE_METRICS + MGS_COUNT_ONLY_METRICS + OSD_CONFIG_METRICS

# OBD filter base metrics
OBDFILTER_BASE = [
    'lustre.obdfilter.read_bytes',
    'lustre.obdfilter.write_bytes',
    'lustre.obdfilter.read',
    'lustre.obdfilter.write',
    'lustre.obdfilter.setattr',
    'lustre.obdfilter.punch',
    'lustre.obdfilter.sync',
    'lustre.obdfilter.destroy',
    'lustre.obdfilter.statfs',
]

# OSS service base metrics
OSS_SERVICE_BASE = [
    'lustre.oss.req_waittime',
    'lustre.oss.req_qdepth',
    'lustre.oss.req_active',
    'lustre.oss.req_timeout',
    'lustre.oss.reqbuf_avail',
    'lustre.oss.ldlm_glimpse_enqueue',
    'lustre.oss.ldlm_extent_enqueue',
    'lustre.oss.ost_setattr',
    'lustre.oss.ost_create',
    'lustre.oss.ost_destroy',
    'lustre.oss.ost_get_info',
    'lustre.oss.ost_connect',
    'lustre.oss.ost_disconnect',
    'lustre.oss.ost_sync',
    'lustre.oss.obd_ping',
]

# OBD filter export base metrics
OBDFILTER_EXPORT_BASE = [
    'lustre.obdfilter.exports.setattr',
    'lustre.obdfilter.exports.destroy',
    'lustre.obdfilter.exports.create',
    'lustre.obdfilter.exports.statfs',
    'lustre.obdfilter.exports.get_info',
    'lustre.obdfilter.exports.read_bytes',
    'lustre.obdfilter.exports.write_bytes',
    'lustre.obdfilter.exports.read',
    'lustre.obdfilter.exports.write',
    'lustre.obdfilter.exports.punch',
    'lustre.obdfilter.exports.sync',
]

# Expand OSS metrics with appropriate suffixes
OBDFILTER_METRICS = _expand_metric_base(OBDFILTER_BASE, EXTENDED_HISTOGRAM_SUFFIXES)
OSS_SERVICE_METRICS = _expand_metric_base(OSS_SERVICE_BASE, EXTENDED_HISTOGRAM_SUFFIXES)
OBDFILTER_EXPORT_METRICS = _expand_metric_base(OBDFILTER_EXPORT_BASE, EXTENDED_HISTOGRAM_SUFFIXES)

# OSS metrics - combination of all OSS-side metrics
OSS_METRICS = OSD_CONFIG_METRICS + OBDFILTER_METRICS + OSS_SERVICE_METRICS + OBDFILTER_EXPORT_METRICS

# Jobstats base metrics
JOBSTATS_OSS_BASE = [
    'job_stats.read_bytes',
    'job_stats.write_bytes',
    'job_stats.read',
    'job_stats.write',
    'job_stats.getattr',
    'job_stats.setattr',
    'job_stats.punch',
    'job_stats.sync',
    'job_stats.destroy',
    'job_stats.create',
    'job_stats.statfs',
    'job_stats.get_info',
    'job_stats.set_info',
    'job_stats.quotactl',
    'job_stats.prealloc',
]

JOBSTATS_MDS_BASE = [
    'job_stats.open',
    'job_stats.close',
    'job_stats.mknod',
    'job_stats.link',
    'job_stats.unlink',
    'job_stats.mkdir',
    'job_stats.rmdir',
    'job_stats.rename',
    'job_stats.getattr',
    'job_stats.setattr',
    'job_stats.getxattr',
    'job_stats.setxattr',
    'job_stats.statfs',
    'job_stats.sync',
    'job_stats.samedir_rename',
    'job_stats.parallel_rename_file',
    'job_stats.parallel_rename_dir',
    'job_stats.crossdir_rename',
    'job_stats.read',
    'job_stats.write',
    'job_stats.read_bytes',
    'job_stats.write_bytes',
    'job_stats.punch',
    'job_stats.migrate',
    'job_stats.fallocate',
]

# Expand jobstats metrics with appropriate suffixes
JOBSTATS_OSS_METRICS = _expand_metric_base(
    [f'lustre.{metric}' for metric in JOBSTATS_OSS_BASE], EXTENDED_HISTOGRAM_SUFFIXES
) + ['lustre.job_stats.read_bytes.bucket', 'lustre.job_stats.write_bytes.bucket']

JOBSTATS_MDS_METRICS = _expand_metric_base(
    [f'lustre.{metric}' for metric in JOBSTATS_MDS_BASE], EXTENDED_HISTOGRAM_SUFFIXES
) + ['lustre.job_stats.read_bytes.bucket', 'lustre.job_stats.write_bytes.bucket']

# Job statistics metrics - combination of OSS and MDS jobstats
JOBSTATS_METRICS = JOBSTATS_OSS_METRICS + JOBSTATS_MDS_METRICS
