# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.jmx import JVM_E2E_METRICS_NEW

METRICS = [
    "hudi.commit.time",
    "hudi.commit.duration",
    "hudi.commit.bytes_written",
    "hudi.commit.compacted_records_updated",
    "hudi.commit.create_time",
    "hudi.commit.files_inserted",
    "hudi.commit.files_updated",
    "hudi.commit.insert_records_written",
    "hudi.commit.log_files_compacted",
    "hudi.commit.log_files_size",
    "hudi.commit.partitions_written",
    "hudi.commit.records_written",
    "hudi.commit.scan_time",
    "hudi.commit.update_records_written",
    "hudi.commit.upsert_time",
    "hudi.finalize.duration",
    "hudi.finalize.num_files",
    "hudi.index.upsert_duration",
    "hudi.index.lookup_duration",
    "hudi.clean_time",
    "hudi.commit_time",
    "hudi.finalize_time",
] + JVM_E2E_METRICS_NEW
