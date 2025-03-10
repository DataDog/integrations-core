# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRIC_CONFIGS_BY_FORMAT_TYPE = {
    "analytics.uploaded_bytes_by_format": {
        "metric_key": "nexus.analytics.bytes_transferred_by_format",
        "value_key": "bytes_uploaded",
        "tag_key": "format",
    },
    "analytics.downloaded_bytes_by_format": {
        "metric_key": "nexus.analytics.bytes_transferred_by_format",
        "value_key": "bytes_downloaded",
        "tag_key": "format",
    },
    "analytics.blob_store.count_by_type": {
        "metric_key": "nexus.analytics.blobstore_type_counts",
        "value_key": "",
        "tag_key": "type",
    },
}

METRIC_CONFIGS = {
    "analytics.gc.g1_old_generation_count": {
        "metric_key": "jvm.garbage-collectors.G1-Old-Generation.count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.gc.g1_young_generation_count": {
        "metric_key": "jvm.garbage-collectors.G1-Young-Generation.count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.gc.g1_old_generation_time": {
        "metric_key": "jvm.garbage-collectors.G1-Old-Generation.time",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.gc.g1_young_generation_time": {
        "metric_key": "jvm.garbage-collectors.G1-Young-Generation.time",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.jvm.heap_memory_max": {"metric_key": "jvm.memory.heap.max", "value_key": "", "tag_key": []},
    "analytics.jvm.heap_memory_used": {"metric_key": "jvm.memory.heap.used", "value_key": "", "tag_key": []},
    "analytics.repository_total_count": {
        "metric_key": "nexus.analytics.repository_total_count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.component_total_count": {
        "metric_key": "nexus.analytics.component_total_count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.log4j_visualizer_non_vulnerable_daily_download_count": {
        "metric_key": "nexus.analytics.log4j_visualizer_non_vulnerable_daily_download_count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.log4j_visualizer_vulnerable_daily_download_count": {
        "metric_key": "nexus.analytics.log4j_visualizer_vulnerable_daily_download_count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.cleanup_dry_run_count": {
        "metric_key": "nexus.analytics.cleanup_dry_run_count",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.cleanup_dry_run_avg_execution_time": {
        "metric_key": "nexus.analytics.cleanup_dry_run_avg_execution_time",
        "value_key": "",
        "tag_key": [],
    },
    "analytics.uptime": {"metric_key": "nexus.analytics.uptime_ms", "value_key": "", "tag_key": []},
    "analytics.blob_store.blobcount_by_type": {
        "metric_key": "nexus.analytics.blobstore_metrics_by_type",
        "value_key": "blob_count",
        "tag_key": ["type"],
    },
    "analytics.blob_store.size_by_type": {
        "metric_key": "nexus.analytics.blobstore_metrics_by_type",
        "value_key": "bytes",
        "tag_key": ["type"],
    },
    "analytics.repository_asset_count_by_format_type": {
        "metric_key": "nexus.analytics.repository_asset_count_by_format_type",
        "value_key": "count",
        "tag_key": ["format", "type"],
    },
    "analytics.repository_count_by_format_type": {
        "metric_key": "nexus.analytics.repository_component_count_by_format_type",
        "value_key": "count",
        "tag_key": ["format", "type"],
    },
    "analytics.malicious_risk_on_disk": {
        "metric_key": "nexus.analytics.malicious_risk_on_disk",
        "value_key": "total_count",
        "tag_key": [],
    },
    "analytics.failed_unique_user_authentication_count": {
        "metric_key": "nexus.analytics.unique_user_authentications_count",
        "value_key": "failed_last_24h",
        "tag_key": [],
    },
    "analytics.successful_unique_user_authentication_count": {
        "metric_key": "nexus.analytics.unique_user_authentications_count",
        "value_key": "successful_last_24h",
        "tag_key": [],
    },
    "analytics.unique_user_count": {
        "metric_key": "nexus.analytics.unique_user_count",
        "value_key": "last_24h",
        "tag_key": [],
    },
    "analytics.total_memory": {
        "metric_key": "nexus.analytics.system_information",
        "value_key": "totalMemory",
        "tag_key": [],
    },
    "analytics.available_cpus": {
        "metric_key": "nexus.analytics.system_information",
        "value_key": "availableCPUs",
        "tag_key": [],
    },
}

STATUS_METRICS_MAP = {
    "Available CPUs": "status.available_cpus_health",
    "Blob Stores Quota": "status.blob_store.quota_health",
    "Blob Stores Ready": "status.blob_store.ready_health",
    "Coordinate Content Selectors": "status.coordinate_content_selectors_health",
    "Default Admin Credentials": "status.default_admin_credentials_health",
    "Default Secret Encryption Key": "status.default_secret_encryption_key_health",
    "DefaultRoleRealm": "status.default_role_realm_health",
    "File Blob Stores Path": "status.blob_store.file_path_health",
    "File Descriptors": "status.file_descriptors_health",
    "Lifecycle Phase": "status.lifecycle_phase_health",
    "NuGet V2 repositories": "status.NuGet_V2_repositories_health",
    "Re-encryption required": "status.re_encryption_required_health",
    "Read-Only Detector": "status.read_only_detector_health",
    "Scheduler": "status.scheduler_health",
    "Scripting": "status.scripting_health",
    "Thread Deadlock Detector": "status.thread_deadlock_detector",
}
