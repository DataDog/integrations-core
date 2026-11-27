# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Mapping
from typing import Any

from kubernetes import client, config
from pydantic import BaseModel

# The Kubernetes client waits forever by default, which would block the check run on a stalled API server.
REQUEST_TIMEOUT = 10


class KubernetesAPIClient:
    def __init__(self, kube_config_dict: BaseModel | Mapping[str, Any] | None = None):
        kube_config_dict = to_mutable_config(kube_config_dict)
        if kube_config_dict:
            self.api_client = config.new_client_from_config_dict(kube_config_dict)
        else:
            config.load_incluster_config()
            self.api_client = client.ApiClient()
        self.custom_objects = client.CustomObjectsApi(self.api_client)
        self.core = client.CoreV1Api(self.api_client)

    def list_podgroups(self) -> list[dict]:
        return self.custom_objects.list_cluster_custom_object(
            group='scheduling.run.ai', version='v2alpha2', plural='podgroups', _request_timeout=REQUEST_TIMEOUT
        )['items']

    def list_evict_events(self, namespace: str) -> list[dict]:
        """Return the `Evict` Kubernetes events that the KAI scheduler recorded on the PodGroups of a namespace."""
        events = self.core.list_namespaced_event(
            namespace, field_selector='involvedObject.kind=PodGroup,reason=Evict', _request_timeout=REQUEST_TIMEOUT
        )
        return self.api_client.sanitize_for_serialization(events)['items']


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
