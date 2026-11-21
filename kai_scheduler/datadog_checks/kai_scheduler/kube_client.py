# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Mapping
from typing import Any

from kubernetes import client, config

# The Kubernetes client waits forever by default, which would block the check run on a stalled API server.
REQUEST_TIMEOUT = 10


class KubernetesAPIClient:
    def __init__(self, kube_config_dict: Mapping[str, Any] | None = None):
        if kube_config_dict:
            self.api_client = config.new_client_from_config_dict(to_mutable_config(kube_config_dict))
        else:
            config.load_incluster_config()
            self.api_client = client.ApiClient()
        self.custom_objects = client.CustomObjectsApi(self.api_client)
        self.core = client.CoreV1Api(self.api_client)
        self.batch = client.BatchV1Api(self.api_client)

    def list_podgroups(self) -> list[dict]:
        return self.custom_objects.list_cluster_custom_object(
            group='scheduling.run.ai', version='v2alpha2', plural='podgroups', _request_timeout=REQUEST_TIMEOUT
        )['items']

    def list_pods(self, field_selector: str | None = None) -> list[dict]:
        """Return the pods of every namespace as JSON, optionally filtered by a field selector."""
        pods = self.core.list_pod_for_all_namespaces(field_selector=field_selector, _request_timeout=REQUEST_TIMEOUT)
        return self.api_client.sanitize_for_serialization(pods)['items']

    def read_job(self, namespace: str, name: str) -> dict | None:
        """Return a batch Job as JSON, or None if it does not exist."""
        try:
            job = self.batch.read_namespaced_job(name, namespace, _request_timeout=REQUEST_TIMEOUT)
        except client.ApiException as e:
            if e.status == 404:
                return None
            raise
        return self.api_client.sanitize_for_serialization(job)

    def list_evict_events(self, namespace: str) -> list[dict]:
        """Return the `Evict` Kubernetes events that the KAI scheduler recorded on the PodGroups of a namespace."""
        events = self.core.list_namespaced_event(
            namespace, field_selector='involvedObject.kind=PodGroup,reason=Evict', _request_timeout=REQUEST_TIMEOUT
        )
        return self.api_client.sanitize_for_serialization(events)['items']


def to_mutable_config(value: Any) -> Any:
    # The configuration models freeze mappings and lists, which the kubernetes client cannot load.
    if isinstance(value, Mapping):
        return {key: to_mutable_config(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_mutable_config(item) for item in value]
    return value
