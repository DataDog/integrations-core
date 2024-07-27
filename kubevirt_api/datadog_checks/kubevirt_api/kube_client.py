# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from kubernetes import client, config


class KubernetesAPIClient:
    def __init__(self, tls_verify=True, kube_api_endpoint=None, kube_config_dict=None):
        self.tls_verify = tls_verify

        if kube_config_dict:
            api_client = config.new_client_from_config_dict(kube_config_dict)
            self.api_client = client.CoreV1Api(api_client=api_client)
        else:
            config.load_incluster_config()
            self.api_client = client.CoreV1Api()

    def get_pods(self, namespace=None, ip=None):
        kwargs = {"watch": False}

        if ip:
            kwargs["field_selector"] = f"status.podIP={ip}"

        if namespace:
            return self.api_client.list_namespaced_pod(namespace, **kwargs).items

        return self.api_client.list_pod_for_all_namespaces(**kwargs).items
