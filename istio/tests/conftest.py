# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

DEPLOYMENTS = [
    ('istio-citadel', 15014),
    ('istio-galley', 15014),
    ('istio-pilot', 15014),
    ('istio-telemetry', 15014),
    ('istio-telemetry', 42422),
    ('istio-ingressgateway', 80),
]


@pytest.fixture(scope='session')
def dd_environment():
    if not os.environ.get('TF_VAR_account_json'):
        pytest.skip('TF_VAR_account_json not set')
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        kubeconfig = outputs['kubeconfig']['value']
        with ExitStack() as stack:
            ports = [
                stack.enter_context(port_forward(kubeconfig, 'istio-system', deployment, port))
                for (deployment, port) in DEPLOYMENTS
            ]
            instance = {
                'citadel_endpoint': 'http://localhost:{}/metrics'.format(ports[0]),
                'galley_endpoint': 'http://localhost:{}/metrics'.format(ports[1]),
                'pilot_endpoint': 'http://localhost:{}/metrics'.format(ports[2]),
                'mixer_endpoint': 'http://localhost:{}/metrics'.format(ports[3]),
                'istio_mesh_endpoint': 'http://localhost:{}/metrics'.format(ports[4]),
            }
            page = 'http://localhost:{}/productpage'.format(ports[5])
            # Check a bit to make sure it's available
            CheckEndpoints([page], wait=5)()
            for _ in range(5):
                # Generate some traffic
                requests.get(page)
            yield instance
