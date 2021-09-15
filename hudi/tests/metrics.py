# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW

METRICS = [
    "hudi.action.duration",
    "hudi.action.bytes_written",
    "hudi.action.compacted_records_updated",
    "hudi.action.create_time",
    "hudi.action.files_inserted",
    "hudi.action.files_updated",
    "hudi.action.insert_records_written",
    "hudi.action.log_files_compacted",
    "hudi.action.log_files_size",
    "hudi.action.partitions_written",
    "hudi.action.records_written",
    "hudi.action.scan_time",
    "hudi.action.update_records_written",
    "hudi.action.upsert_time",
    "hudi.finalize.duration",
    "hudi.finalize.num_files",
    "hudi.index.command.duration",
    "hudi.clean_time",
    "hudi.commit_time",
    "hudi.action.time.min",
    "hudi.action.time.max",
    "hudi.action.time.count",
] + JVM_E2E_METRICS_NEW
