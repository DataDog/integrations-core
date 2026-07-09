# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Mapping
from typing import Any

from kubernetes import client, config


class KubernetesAPIClient:
    def __init__(self, log=None, kube_config_dict: Mapping[str, Any] | None = None):
        self.log = log

        if kube_config_dict:
            api_client = config.new_client_from_config_dict(to_mutable_config(kube_config_dict))
            self.custom_obj_client = client.CustomObjectsApi(api_client=api_client)
        else:
            if self.log:
                self.log.debug('Using load_incluster_config to configure the kube client')
            config.load_incluster_config()
            self.custom_obj_client = client.CustomObjectsApi()

    def list_workloads(self, namespace: str | None = None) -> list[dict]:
        if namespace:
            return self.custom_obj_client.list_namespaced_custom_object(
                group='kueue.x-k8s.io',
                version='v1beta1',
                namespace=namespace,
                plural='workloads',
            )['items']

        return self.custom_obj_client.list_cluster_custom_object(
            group='kueue.x-k8s.io',
            version='v1beta1',
            plural='workloads',
        )['items']


def to_mutable_config(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: to_mutable_config(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_mutable_config(item) for item in value]
    return value
