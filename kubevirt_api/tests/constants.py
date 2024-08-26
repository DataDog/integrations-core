# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


HEALTHZ_TAGS = [
    "endpoint:https://10.244.0.38:443/healthz",
    "pod_name:virt-api-98cf864cc-zkgcd",
    "kube_namespace:kubevirt",
]

BAD_METRICS_HOSTNAME_INSTANCE = {
    "kubevirt_api_metrics_endpoint": "https://bad_endpoint:443/metrics",
    "kubevirt_api_healthz_endpoint": "https://10.244.0.38:443/healthz",
    "kube_namespace": "kubevirt",
    "kube_pod_name": "virt-api-98cf864cc-zkgcd",
}
