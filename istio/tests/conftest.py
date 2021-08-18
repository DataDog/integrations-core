# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()


@pytest.fixture(scope='session')
def dd_environment():
    version = os.environ.get("ISTIO_VERSION")

    with terraform_run(os.path.join(HERE, 'terraform', version)) as outputs:
        kubeconfig = outputs['kubeconfig']['value']
        with ExitStack() as stack:
            if version == '1.5.1':
                istiod_host, istiod_port = stack.enter_context(port_forward(kubeconfig, 'istio-system', 'istiod', 8080))
                instance = {'istiod_endpoint': 'http://{}:{}/metrics'.format(istiod_host, istiod_port)}

                yield instance
