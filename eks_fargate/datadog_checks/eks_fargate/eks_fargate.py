# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
import os

class EksFargateCheck(AgentCheck):
    def check(self, instance):
        virtual_node = os.getenv("DD_KUBERNETES_KUBELET_NODENAME")
        pod_name = os.getenv("HOSTNAME")
        # Only submit the heartbeat metric for fargate virtual nodes.
        if "fargate" in virtual_node:
            tags = [] 
            tags.append("pod_name:" + pod_name)
            tags.append("virtual_node:"+ virtual_node)
            self.gauge("eks.fargate.pods.running", 1, tags)
