# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

GENERIC_METRIC_MAP = {}

PIPELINES_METRIC = {
    'tekton_pipelines_controller_go_alloc': 'go_alloc',
}

TRIGGERS_METRIC = {
    "controller_clusterinterceptor_count": "clusterinterceptor",
}

PIPELINES_METRIC_MAP = [PIPELINES_METRIC | GENERIC_METRIC_MAP]
TRIGGERS_METRIC_MAP = [TRIGGERS_METRIC | GENERIC_METRIC_MAP]

ENDPOINTS_METRICS_MAP = {
    "pipelines_controller_endpoint": PIPELINES_METRIC_MAP,
    "triggers_controller_endpoint": TRIGGERS_METRIC_MAP,
}
