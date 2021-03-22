# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os
from datetime import datetime, timedelta

from kubeutil import get_connection_info

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.date import UTC
from datadog_checks.base.utils.tagging import tagger

from .common import ExpiredPodFilter, KubeletCredentials

try:
    from datadog_agent import get_config
except ImportError:

    def get_config(key):
        return ""


KUBELET_NODE_ENV_VAR = 'DD_KUBERNETES_KUBELET_NODENAME'
CAPACITY_ANNOTATION_KEY = 'CapacityProvisioned'
POD_LIST_PATH = '/pods'
GB_TO_BYTE_CONVERSION_FACTOR = 1024 * 1024 * 1024

log = logging.getLogger('collector')


class EksFargateCheck(AgentCheck):
    """
    Generate heartbeat and capacity metrics for Amazon EKS on AWS Fargate workloads
    """

    def __init__(self, name, init_config, instances):
        super(EksFargateCheck, self).__init__(name, init_config, instances)
        self.NAMESPACE = 'eks.fargate'

        virtual_node = os.getenv(KUBELET_NODE_ENV_VAR, "")
        self.fargate_mode = 'fargate' in virtual_node

        kubelet_conn_info = get_connection_info()
        endpoint = kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically: " + kubelet_conn_info.get('err', ''))

        self.pod_list_url = endpoint.strip("/") + POD_LIST_PATH
        self.kubelet_credentials = KubeletCredentials(kubelet_conn_info)

        if self.fargate_mode:
            self.tags = []
            self.tags.append('virtual_node:' + virtual_node)
            self.tags.extend(instances[0].get('tags', []))

    def check(self, instance):
        if self.fargate_mode:
            pod_list = self.get_pod_list()
            for pod in pod_list.get('items', []):
                pod_id = pod.get('metadata', {}).get('uid')
                tagger_tags = tagger.tag('kubernetes_pod_uid://%s' % pod_id, tagger.ORCHESTRATOR) or []
                tagger_tags.extend(self.tags)
                tags = set(tagger_tags)
                # Submit the heartbeat metric for fargate virtual nodes.
                self.gauge(self.NAMESPACE + '.pods.running', 1, tags)
                pod_annotations = pod.get('metadata', {}).get('annotations')
                if CAPACITY_ANNOTATION_KEY not in pod_annotations:
                    continue
                cpu_val, mem_val = extract_resource_values(pod_annotations.get(CAPACITY_ANNOTATION_KEY))
                if cpu_val == 0 or mem_val == 0:
                    continue
                self.gauge(self.NAMESPACE + '.cpu.capacity', cpu_val, tags)
                self.gauge(self.NAMESPACE + '.memory.capacity', mem_val, tags)

    def perform_kubelet_query(self, url):
        """
        Perform and return a GET request against kubelet. Support auth and TLS validation.
        """
        return self.http.get(
            url,
            verify=self.kubelet_credentials.verify(),
            cert=self.kubelet_credentials.cert_pair(),
            headers=self.kubelet_credentials.headers(url),
            params={'verbose': True},
            stream=True,
        )

    def get_pod_list(self):
        try:
            cutoff_date = compute_pod_expiration_datetime()
            with self.perform_kubelet_query(self.pod_list_url) as r:
                if cutoff_date:
                    f = ExpiredPodFilter(cutoff_date)
                    pod_list = json.load(r.raw, object_hook=f.json_hook)
                    pod_list['expired_count'] = f.expired_count
                    if pod_list.get('items') is not None:
                        # Filter out None items from the list
                        pod_list['items'] = [p for p in pod_list['items'] if p is not None]
                else:
                    pod_list = json.load(r.raw)

            if pod_list.get('items') is None:
                # Sanitize input: if no pods are running, 'items' is a NoneObject
                pod_list['items'] = []
            return pod_list
        except Exception as e:
            self.log.warning("failed to retrieve pod list from the kubelet at %s : %s", self.pod_list_url, e)
            return {}


def extract_resource_values(capacity_annotation):
    """
    Given pod annotations, extract the resource values for submission as metrics
    Example input: "0.25vCPU 0.5GB"
    """
    cpu_val, mem_val = 0, 0
    capacities = capacity_annotation.split(" ")
    if len(capacities) != 2:
        return cpu_val, mem_val
    cpu, mem = capacities
    if cpu.endswith('vCPU'):
        cpu_val = float(cpu.strip('vCPU'))
    if mem.endswith('GB'):
        mem_val = float(mem.strip('GB'))
        mem_val *= GB_TO_BYTE_CONVERSION_FACTOR
    return cpu_val, mem_val


def compute_pod_expiration_datetime():
    try:
        seconds = int(get_config('kubernetes_pod_expiration_duration'))
        # expiration disabled
        if seconds == 0:
            return None
        return datetime.utcnow().replace(tzinfo=UTC) - timedelta(seconds=seconds)
    except (ValueError, TypeError):
        return None
