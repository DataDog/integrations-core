# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.pulsar import PulsarCheck

from . import common

INTEGRATIONS_CORE_ROOT = Path(__file__).resolve().parents[2]
PULSAR_AUTOCONF = Path(__file__).parent.parent / "datadog_checks" / "pulsar" / "data" / "auto_conf_discovery.yaml"
DISCOVERY_HELPERS_DIR = (
    INTEGRATIONS_CORE_ROOT / "datadog_checks_base" / "datadog_checks" / "base" / "utils" / "discovery"
)
OPENMETRICS_V2_BASE_PY = (
    INTEGRATIONS_CORE_ROOT
    / "datadog_checks_base"
    / "datadog_checks"
    / "base"
    / "checks"
    / "openmetrics"
    / "v2"
    / "base.py"
)
AGENTCHECK_BASE_PY = INTEGRATIONS_CORE_ROOT / "datadog_checks_base" / "datadog_checks" / "base" / "checks" / "base.py"
SITE_PACKAGES = "/opt/datadog-agent/embedded/lib/python3.13/site-packages"


@pytest.fixture(scope='session')
def dd_environment(instance):
    env_vars = {'PULSAR_VERSION': common.PULSAR_VERSION}
    with docker_run(
        os.path.join(common.HERE, 'docker', 'docker-compose.yaml'),
        env_vars=env_vars,
        endpoints=instance['openmetrics_endpoint'],
        mount_logs=True,
        sleep=10,
    ):
        yield (
            instance,
            {
                'docker_volumes': [
                    f"{PULSAR_AUTOCONF}:/etc/datadog-agent/conf.d/pulsar.d/auto_conf_discovery.yaml:ro",
                    f"{DISCOVERY_HELPERS_DIR}:{SITE_PACKAGES}/datadog_checks/base/utils/discovery:ro",
                    f"{OPENMETRICS_V2_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/openmetrics/v2/base.py:ro",
                    f"{AGENTCHECK_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/base.py:ro",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                ],
            },
        )


@pytest.fixture(scope='session')
def instance():
    return {'openmetrics_endpoint': common.METRICS_URL}


@pytest.fixture(scope='session')
def pulsar_check():
    return lambda instance: PulsarCheck('pulsar', {}, [instance])
