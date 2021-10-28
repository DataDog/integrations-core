# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

from kubeutil import get_connection_info

from datadog_checks.base.checks.kubelet_base.base import KubeletBase, KubeletCredentials
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.tagging import tagger

KUBELET_NODE_ENV_VAR = 'DD_KUBERNETES_KUBELET_NODENAME'
CAPACITY_ANNOTATION_KEY = 'CapacityProvisioned'
POD_LIST_PATH = '/pods'
GB_TO_BYTE_CONVERSION_FACTOR = 1024 * 1024 * 1024

log = logging.getLogger('collector')


class EksFargateCheck(KubeletBase):
    """
    Generate heartbeat and capacity metrics for Amazon EKS on AWS Fargate workloads
    """

    def __init__(self, name, init_config, instances):
        super(EksFargateCheck, self).__init__(name, init_config, instances)
        self.NAMESPACE = 'eks.fargate'

        virtual_node = os.getenv(KUBELET_NODE_ENV_VAR, "")
        self.fargate_mode = 'fargate' in virtual_node

        if self.fargate_mode:
            self.tags = []
            self.tags.append('virtual_node:' + virtual_node)
            self.tags.extend(instances[0].get('tags', []))

    def check(self, _):
        kubelet_conn_info = get_connection_info()
        endpoint = kubelet_conn_info.get('url')
        if endpoint is None:
            raise CheckException("Unable to detect the kubelet URL automatically: " + kubelet_conn_info.get('err', ''))

        self.pod_list_url = endpoint.strip("/") + POD_LIST_PATH
        self.kubelet_credentials = KubeletCredentials(kubelet_conn_info)

        if self.fargate_mode:
            pod_list = self.retrieve_pod_list()
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
