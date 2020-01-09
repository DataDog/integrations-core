# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.eks_fargate import EksFargateCheck
import os

def test_eksfargate(aggregator, instance):
    os.environ["DD_KUBERNETES_KUBELET_NODENAME"] = "fargate-foo"
    os.environ["HOSTNAME"] = "bar"
    check = EksFargateCheck('eks_fargate', {}, [{}])
    check.check(instance)
    aggregator.assert_metric("eks.fargate.pods.running", value=1, tags=["virtual_node:fargate-foo","pod_name:bar"])

def test_not_eksfargate(aggregator, instance):
    os.environ["DD_KUBERNETES_KUBELET_NODENAME"] = "foo"
    check = EksFargateCheck('eks_fargate', {}, [{}])
    check.check(instance)
    assert "eks.fargate.pods.running" not in aggregator._metrics