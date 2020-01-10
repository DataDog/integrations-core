# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import AgentCheck


class EksFargateCheck(AgentCheck):
    """
    Generate a heartbeat for Amazon EKS on AWS Fargate workloads
    """

    def __init__(self, name, init_config, instances):
        super(EksFargateCheck, self).__init__(
            name, init_config, instances,
        )
        self.pod_name = os.getenv("HOSTNAME")
        self.virtual_node = os.getenv("DD_KUBERNETES_KUBELET_NODENAME")

    def check(self, instance):

        # Only submit the heartbeat metric for fargate virtual nodes.
        if "fargate" in self.virtual_node:
            tags = []

            tags.append("pod_name:" + self.pod_name)
            tags.append("virtual_node:" + self.virtual_node)
            tags = tags + instance.get('tags', [])

            self.gauge("eks.fargate.pods.running", 1, tags)
