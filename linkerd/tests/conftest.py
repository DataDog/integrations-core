import os

import pytest

from datadog_checks.dev import run_command
from datadog_checks.dev.kind import kind_run

from .common import E2E_METADATA, LINKERD_FIXTURE_METRICS, LINKERD_FIXTURE_TYPES

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


def setup_linkerd():
    result = run_command(
        ["kind", "get", "kubeconfig", "--internal", "--name", "cluster-linkerd-py38"],
        capture='out',
        check=True,
    )
    with open('/tmp/kubeconfig.yaml', 'w') as f:
        f.write(result.stdout)
    run_command(['cat', '/tmp/kubeconfig.yaml'], check=True, shell=True)


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_linkerd]) as kubeconfig:
        instance = {
            'prometheus_url': 'http://localhost:9990/metrics',
            'metrics': [LINKERD_FIXTURE_METRICS],
            'type_overrides': LINKERD_FIXTURE_TYPES,
        }
        yield instance, E2E_METADATA
