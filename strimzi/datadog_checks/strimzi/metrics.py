# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COMMON_METRICS_MAP = {
    "jvm_gc_memory_promoted_bytes": "jvm.gc.memory_promoted_bytes",
}

CLUSTER_OPERATOR_METRICS_MAP = {}
CLUSTER_OPERATOR_METRICS_MAP.update(COMMON_METRICS_MAP)

TOPIC_OPERATOR_METRICS_MAP = {}
TOPIC_OPERATOR_METRICS_MAP.update(COMMON_METRICS_MAP)

USER_OPERATOR_METRICS_MAP = {}
USER_OPERATOR_METRICS_MAP.update(COMMON_METRICS_MAP)
