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
        super(EksFargateCheck, self).__init__(name, init_config, instances)
        pod_name = os.getenv("HOSTNAME")
        virtual_node = os.getenv("DD_KUBERNETES_KUBELET_NODENAME", "")

        self.fargate_mode = 'fargate' in virtual_node

        if pod_name is not None and self.fargate_mode:
            self.tags = []
            self.tags.append("pod_name:" + pod_name)
            self.tags.append("virtual_node:" + virtual_node)
            self.tags.extend(instances[0].get('tags', []))

    def check(self, _):

        # Only submit the heartbeat metric for fargate virtual nodes.
        if self.fargate_mode:
            self.gauge("eks.fargate.pods.running", 1, self.tags)
