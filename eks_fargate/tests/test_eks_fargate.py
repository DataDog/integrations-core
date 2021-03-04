# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.dev import EnvVars
from datadog_checks.eks_fargate import EksFargateCheck
from datadog_checks.eks_fargate.eks_fargate import HOSTNAME_ENV_VAR, KUBELET_NODE_ENV_VAR, extract_resource_values

HERE = os.path.abspath(os.path.dirname(__file__))


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname)) as f:
        return f.read()


def test_eksfargate(monkeypatch, aggregator):
    with EnvVars(
        {
            KUBELET_NODE_ENV_VAR: 'fargate-foo',
            HOSTNAME_ENV_VAR: 'bar',
        }
    ):
        instance = {'tags': ['foo:bar']}
        check = EksFargateCheck('eks_fargate', {}, [instance])
        monkeypatch.setattr(check, 'pod_list', json.loads(mock_from_file('pods.json')))
        check.check(instance)
        aggregator.assert_metric(
            check.NAMESPACE + '.pods.running', value=1, tags=['virtual_node:fargate-foo', 'pod_name:bar', 'foo:bar']
        )
        aggregator.assert_metric(
            check.NAMESPACE + '.capacity.cpu', value=0.25, tags=['virtual_node:fargate-foo', 'pod_name:bar', 'foo:bar']
        )
        aggregator.assert_metric(
            check.NAMESPACE + '.capacity.memory',
            value=0.5,
            tags=['virtual_node:fargate-foo', 'pod_name:bar', 'foo:bar'],
        )


def test_not_eksfargate(monkeypatch, aggregator):
    with EnvVars(
        {
            KUBELET_NODE_ENV_VAR: 'foo',
        }
    ):
        instance = {}
        check = EksFargateCheck('eks_fargate', {}, [instance])
        monkeypatch.setattr(check, 'pod_list', json.loads(mock_from_file('pods.json')))
        check.check(instance)
        assert check.NAMESPACE + '.pods.running' not in aggregator._metrics
        assert check.NAMESPACE + '.capacity.cpu' not in aggregator._metrics
        assert check.NAMESPACE + '.capacity.memory' not in aggregator._metrics


def test_extract_resource_values():
    test_input = '0.25vCPU 0.5GB'
    cpu, mem = extract_resource_values(test_input)
    assert cpu == 0.25
    assert mem == 0.5

    test_input = '0.25vCPUa 0.5GB'
    cpu, mem = extract_resource_values(test_input)
    assert cpu == 0
    assert mem == 0.5

    test_input = '0.25vCPU 0.5GBa'
    cpu, mem = extract_resource_values(test_input)
    assert cpu == 0.25
    assert mem == 0
