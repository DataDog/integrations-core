# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW

METRICS = [
    # metrics commented out can be emitted but not without adding more complex updates to the environment
    # "hudi.clean.duration",
    # "hudi.clean.files_deleted"
    # "hudi.rollback.files_deleted",
    # "hudi.rollback.duration",
    "hudi.action.insert_records_written",
    "hudi.action.duration",
    "hudi.action.bytes_written",
    "hudi.action.compacted_records_updated",
    "hudi.action.create_time",
    "hudi.action.files_inserted",
    "hudi.action.files_updated",
    "hudi.action.log_files_compacted",
    "hudi.action.log_files_size",
    "hudi.action.partitions_written",
    "hudi.action.records_written",
    "hudi.action.scan_time",
    "hudi.action.update_records_written",
    "hudi.action.upsert_time",
    "hudi.finalize.duration",
    "hudi.finalize.files_finalized",
    "hudi.index.command.duration",
    "hudi.action.commit_time",
    "hudi.action.time.min",
    "hudi.action.time.max",
    "hudi.action.time.count",
    "hudi.action.time.50th_percentile",
    "hudi.action.time.75th_percentile",
    "hudi.action.time.95th_percentile",
    "hudi.action.time.98th_percentile",
    "hudi.action.time.999th_percentile",
    "hudi.action.time.99th_percentile",
    "hudi.action.time.mean",
    "hudi.action.time.std_dev",
] + JVM_E2E_METRICS_NEW
