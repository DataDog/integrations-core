# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from kubernetes import client, config


class KubernetesAPIClient:
    def __init__(self, log=None, kube_config_dict=None):
        self.log = log

        if kube_config_dict:
            self.log.debug("Using kube_config_dict to configure the kube client")
            api_client = config.new_client_from_config_dict(kube_config_dict)
            self.api_client = client.CoreV1Api(api_client=api_client)
            self.custom_obj_client = client.CustomObjectsApi(api_client=api_client)
        else:
            self.log.debug("Using load_incluster_config to configure the kube client")
            config.load_incluster_config()
            self.api_client = client.CoreV1Api()
            self.custom_obj_client = client.CustomObjectsApi()

    def get_pods(self, namespace=None, ip=None):
        kwargs = {"watch": False}

        if ip:
            kwargs["field_selector"] = f"status.podIP={ip}"

        if namespace:
            return self.api_client.list_namespaced_pod(namespace, **kwargs).to_dict()["items"]

        return self.api_client.list_pod_for_all_namespaces(**kwargs).to_dict()["items"]

    def get_vms(self, namespace=None):
        if namespace:
            return self.custom_obj_client.list_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachines",
            )["items"]

        return self.custom_obj_client.list_cluster_custom_object(
            group="kubevirt.io",
            version="v1",
            plural="virtualmachines",
        )["items"]

    def get_vmis(self, namespace=None):
        if namespace:
            return self.custom_obj_client.list_namespaced_custom_object(
                group="kubevirt.io",
                version="v1",
                namespace=namespace,
                plural="virtualmachineinstances",
            )["items"]

        return self.custom_obj_client.list_cluster_custom_object(
            group="kubevirt.io",
            version="v1",
            plural="virtualmachineinstances",
        )["items"]
