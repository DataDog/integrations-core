# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.base.utils.tagging import tagger
from datadog_checks.kubevirt_handler.config_models.discovery import candidates
from datadog_checks.kubevirt_handler.config_models.discovery_strategies import container_tagger_entity_id


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


def test_container_tagger_entity_id():
    assert container_tagger_entity_id('containerd://abc') == 'container_id://abc'
    assert container_tagger_entity_id('docker://abc') == 'container_id://abc'
    assert container_tagger_entity_id('container_id://abc') == 'container_id://abc'
    assert container_tagger_entity_id('abc') == 'abc'


def test_candidates_use_kubernetes_tags():
    tagger.set_tags(
        {
            'container_id://abc': [
                'kube_namespace:kubevirt',
                'pod_name:virt-handler-abc',
            ],
        }
    )
    service = Service(
        id='containerd://abc',
        host='10.0.0.5',
        ports=(Port(number=8443, name='metrics'), Port(number=8080, name='http')),
    )

    generated = list(candidates(service))

    assert len(generated) == 1
    assert len(generated[0]['instances']) == 1
    expected = {
        'kubevirt_handler_metrics_endpoint': 'https://10.0.0.5:8443/metrics',
        'kubevirt_handler_healthz_endpoint': 'https://10.0.0.5:8443/healthz',
        'kube_namespace': 'kubevirt',
        'kube_pod_name': 'virt-handler-abc',
        'tls_verify': False,
    }
    instance = generated[0]['instances'][0]
    for key, value in expected.items():
        assert instance[key] == value
    tagger.assert_called('container_id://abc', tagger.ORCHESTRATOR)


@pytest.mark.parametrize(
    'tags',
    [
        [],
        ['kube_namespace:kubevirt'],
        ['pod_name:virt-handler-abc'],
    ],
)
def test_candidates_require_kubernetes_identity_tags(tags):
    tagger.set_tags({'container_id://abc': tags})
    service = Service(
        id='containerd://abc',
        host='10.0.0.5',
        ports=(Port(number=8443, name='metrics'),),
    )

    assert list(candidates(service)) == []


def test_candidates_require_named_metrics_port():
    tagger.set_tags({'container_id://abc': ['kube_namespace:kubevirt', 'pod_name:virt-handler-abc']})
    service = Service(
        id='containerd://abc',
        host='10.0.0.5',
        ports=(Port(number=8443, name='http'),),
    )

    assert list(candidates(service)) == []
