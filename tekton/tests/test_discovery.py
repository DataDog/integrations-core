# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.base.utils.discovery import Service
from datadog_checks.tekton.config_models.discovery import candidates


def discovery_candidates(container_name, ports=()):
    """Generate candidates for a service whose container is tagged as ``container_name``."""
    tagger.set_tags({f'container_id://{container_name}': [f'kube_container_name:{container_name}']})
    try:
        service = Service(id=f'docker://{container_name}', host='10.244.0.1', ports=ports)
        return list(candidates(service))
    finally:
        tagger.reset()


@pytest.mark.parametrize(
    'container_name, ports, endpoint_field, endpoint_port',
    [
        pytest.param(
            'tekton-pipelines-controller',
            ({'number': 9090, 'name': 'metrics'},),
            'pipelines_controller_endpoint',
            9090,
            id='pipelines-controller-declared-metrics-port',
        ),
        pytest.param(
            'tekton-pipelines-controller',
            (),
            'pipelines_controller_endpoint',
            9090,
            id='pipelines-controller-default-port',
        ),
        pytest.param(
            'tekton-triggers-controller',
            (),
            'triggers_controller_endpoint',
            9000,
            id='triggers-controller-default-port',
        ),
        pytest.param(
            'tekton-triggers-controller',
            ({'number': 9095, 'name': 'metrics'},),
            'triggers_controller_endpoint',
            9095,
            id='triggers-controller-declared-metrics-port',
        ),
    ],
)
def test_discovery_candidates(container_name, ports, endpoint_field, endpoint_port):
    # Exactly one candidate must be generated, targeting the controller the container actually is.
    (candidate,) = discovery_candidates(container_name, ports=ports)

    [instance] = candidate['instances']
    assert instance[endpoint_field] == f'http://10.244.0.1:{endpoint_port}/metrics'

    other_field = (
        'triggers_controller_endpoint'
        if endpoint_field == 'pipelines_controller_endpoint'
        else 'pipelines_controller_endpoint'
    )
    assert not instance[other_field]


def test_discovery_candidates_unknown_container():
    # A container matching ad_identifiers but with an unknown kube_container_name (e.g. a
    # deployment that renamed its containers) must not get a wrong-endpoint candidate.
    assert discovery_candidates('some-other-controller') == []
