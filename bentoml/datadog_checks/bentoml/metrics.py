# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRICS = {
    "bentoml_service_request_in_progress": "service.request.in_progress",
    "bentoml_service_request": "service.request",
    "bentoml_service_request_duration_seconds": "service.request.duration",
    "bentoml_service_adaptive_batch_size": "service.adaptive_batch_size",
    "bentoml_service_last_request_timestamp_seconds": {
        "type": "time_elapsed",
        "name": "service.time_since_last_request",
    },
}

ENDPOINT_METRICS = {
    "/livez": "endpoint_livez",
    "/readyz": "endpoint_readyz",
}
