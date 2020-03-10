import os

import pytest

from datadog_checks.base import to_native_string
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here

from .common import LINKERD_FIXTURE_METRICS, LINKERD_FIXTURE_TYPES


@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        kubeconfig = to_native_string(outputs['kubeconfig']['value'])

        with port_forward(kubeconfig, 'linkerd', 'linkerd-controller', 4191) as (ip, port):
            instance = {
                'prometheus_url': 'http://{}:{}/metrics'.format(ip, port),
                'metrics': [LINKERD_FIXTURE_METRICS],
                'type_overrides': LINKERD_FIXTURE_TYPES,
            }
            yield instance
