# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Mapping
from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel


class KubernetesAPIClient:
    def __init__(self, log=None, kube_config_dict: BaseModel | Mapping[str, Any] | None = None):
        self.log = log

        kube_config_dict = to_mutable_config(kube_config_dict)
        if kube_config_dict:
            api_client = config.new_client_from_config_dict(kube_config_dict)
            self.custom_obj_client = client.CustomObjectsApi(api_client=api_client)
        else:
            if self.log:
                self.log.debug('Using load_incluster_config to configure the kube client')
            config.load_incluster_config()
            self.custom_obj_client = client.CustomObjectsApi()

    def list_workloads(self, namespace: str | None = None) -> list[dict]:
        try:
            return self.list_workloads_for_version('v1beta2', namespace)
        except ApiException as e:
            if e.status != 404:
                raise
            return self.list_workloads_for_version('v1beta1', namespace)

    def list_workloads_for_version(self, version: str, namespace: str | None) -> list[dict]:
        if namespace:
            return self.custom_obj_client.list_namespaced_custom_object(
                group='kueue.x-k8s.io',
                version=version,
                namespace=namespace,
                plural='workloads',
            )['items']

        return self.custom_obj_client.list_cluster_custom_object(
            group='kueue.x-k8s.io',
            version=version,
            plural='workloads',
        )['items']


def to_mutable_config(value: Any) -> Any:
    # The configuration models turn the kubeconfig into frozen models, mappings and tuples, which the kubernetes
    # client cannot load. Dump the models with their kubeconfig key names, and only the keys that were set.
    if isinstance(value, BaseModel):
        value = value.model_dump(by_alias=True, exclude_unset=True)
    if isinstance(value, Mapping):
        return {key: to_mutable_config(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_mutable_config(item) for item in value]
    return value
