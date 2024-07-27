# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from kubernetes import client, config

from datadog_checks.base.agent import datadog_agent

KUBERNETES_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
KUBERNETES_CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


class KubernetesAPIClient:
    def __init__(self, tls_verify=True):
        self.tls_verify = tls_verify
        kubeconfig_path = datadog_agent.get_config("kubernetes_kubeconfig_path")
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
        else:
            config.load_kube_config()
        # else:
        #     config.load_incluster_config()

        self.api_client = client.CoreV1Api()

    def get_token(self):
        with open(KUBERNETES_TOKEN_PATH, "r") as f:
            return f.read()

    def get_cert(self):
        with open(KUBERNETES_CA_CERT_PATH, "r") as f:
            return f.read()

    def get_pods(self, namespace=None, ip=None):
        kwargs = {"watch": False}

        if ip:
            kwargs["field_selector"] = f"status.podIP={ip}"

        if namespace:
            return self.api_client.list_namespaced_pod(namespace, **kwargs).items

        return self.api_client.list_pod_for_all_namespaces(**kwargs).items
