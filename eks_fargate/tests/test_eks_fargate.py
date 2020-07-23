# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import EnvVars
from datadog_checks.eks_fargate import EksFargateCheck


def test_eksfargate(aggregator):
    with EnvVars({'DD_KUBERNETES_KUBELET_NODENAME': 'fargate-foo', 'HOSTNAME': 'bar'}):
        instance = {'tags': ['foo:bar']}
        check = EksFargateCheck('eks_fargate', {}, [instance])
        check.check(instance)
        aggregator.assert_metric(
            "eks.fargate.pods.running", value=1, tags=["virtual_node:fargate-foo", "pod_name:bar", "foo:bar"]
        )


def test_not_eksfargate(aggregator):
    with EnvVars({'DD_KUBERNETES_KUBELET_NODENAME': 'foo'}):
        instance = {}
        check = EksFargateCheck('eks_fargate', {}, [instance])
        check.check(instance)
        assert "eks.fargate.pods.running" not in aggregator._metrics
