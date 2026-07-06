# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Mapping
from typing import Any

from kubernetes import client, config

KUEUE_API_GROUP = 'kueue.x-k8s.io'
KUEUE_WORKLOAD_API_VERSION = 'v1beta1'
KUEUE_API_VERSION = 'v1beta2'


class KubernetesAPIClient:
    def __init__(self, log=None, kube_config_dict: Mapping[str, Any] | None = None):
        self.log = log

        if kube_config_dict:
            api_client = config.new_client_from_config_dict(to_mutable_config(kube_config_dict))
            self.custom_obj_client = client.CustomObjectsApi(api_client=api_client)
            self.core_v1_client = client.CoreV1Api(api_client=api_client)
        else:
            if self.log:
                self.log.debug('Using load_incluster_config to configure the kube client')
            config.load_incluster_config()
            self.custom_obj_client = client.CustomObjectsApi()
            self.core_v1_client = client.CoreV1Api()

    def list_workloads(self, namespace: str | None = None) -> list[dict]:
        if namespace:
            return self.custom_obj_client.list_namespaced_custom_object(
                group=KUEUE_API_GROUP,
                version=KUEUE_WORKLOAD_API_VERSION,
                namespace=namespace,
                plural='workloads',
            )['items']

        return self.custom_obj_client.list_cluster_custom_object(
            group=KUEUE_API_GROUP,
            version=KUEUE_WORKLOAD_API_VERSION,
            plural='workloads',
        )['items']

    def list_nodes(self) -> list[dict]:
        response = self.core_v1_client.list_node(_preload_content=False)
        return self._json_response_items(response)

    def list_pods(self) -> list[dict]:
        response = self.core_v1_client.list_pod_for_all_namespaces(
            field_selector='status.phase!=Succeeded,status.phase!=Failed',
            _preload_content=False,
        )
        return self._json_response_items(response)

    def list_resource_flavors(self) -> list[dict]:
        return self.custom_obj_client.list_cluster_custom_object(
            group=KUEUE_API_GROUP,
            version=KUEUE_API_VERSION,
            plural='resourceflavors',
        )['items']

    def list_topologies(self) -> list[dict]:
        return self.custom_obj_client.list_cluster_custom_object(
            group=KUEUE_API_GROUP,
            version=KUEUE_API_VERSION,
            plural='topologies',
        )['items']

    @staticmethod
    def _json_response_items(response) -> list[dict]:
        data = response.data.decode('utf-8') if isinstance(response.data, bytes) else response.data
        return json.loads(data)['items']


def to_mutable_config(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: to_mutable_config(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_mutable_config(item) for item in value]
    if isinstance(value, list):
        return [to_mutable_config(item) for item in value]
    return value
