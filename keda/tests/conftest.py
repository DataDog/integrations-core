# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest

from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

from . import common

HERE = common.HERE
CHECK_ROOT = os.path.dirname(HERE)


def setup_ked():
    run_command(['kubectl', 'create', 'ns', 'keda'])
    # The ScaledJob CRD is too large for client-side apply, whose last-applied-configuration
    # annotation would exceed the annotation size limit; the CRD would silently fail to install
    # and the operator would crash-loop waiting for its cache to sync.
    run_command(['kubectl', 'apply', '--server-side', '-f', os.path.join(HERE, 'kind', 'keda_install.yaml')])

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    run_command(['kubectl', 'rollout', 'status', 'deployment/keda-operator-metrics-apiserver', '-n', 'keda'])
    run_command(['kubectl', 'wait', 'pods', '--all', '-n', 'keda', '--for=condition=Ready', '--timeout=600s'])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_ked], sleep=30) as kubeconfig:
        instances = [
            {'openmetrics_endpoint': ('http://keda-operator-metrics-apiserver.keda.svc.cluster.local:8080/metrics')}
        ]

        dd_save_state('keda_kubeconfig', kubeconfig)

        yield (
            {'instances': instances},
            {
                'agent_type': 'kubernetes',
                'kubernetes': {
                    'kubeconfig': kubeconfig,
                    'auto_conf': os.path.join(CHECK_ROOT, 'datadog_checks', 'keda', 'data', 'auto_conf.yaml'),
                },
            },
        )


@pytest.fixture(scope='session')
def keda_kubeconfig(dd_get_state):
    return dd_get_state('keda_kubeconfig')


@pytest.fixture
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)
