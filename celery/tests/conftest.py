# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common

INTEGRATIONS_CORE_ROOT = Path(__file__).resolve().parents[2]
CELERY_AUTOCONF = Path(__file__).parent.parent / "datadog_checks" / "celery" / "data" / "auto_conf_discovery.yaml"
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
SITE_PACKAGES = "/opt/datadog-agent/embedded/lib/python3.13/site-packages"


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE

    with docker_run(
        compose_file,
        conditions=[
            CheckDockerLogs(compose_file, 'Ready to accept connections tcp', service='redis-standalone'),
            CheckEndpoints(common.MOCKED_INSTANCE['openmetrics_endpoint']),
        ],
    ):
        yield (
            common.MOCKED_INSTANCE,
            {
                'docker_volumes': [
                    f"{CELERY_AUTOCONF}:/etc/datadog-agent/conf.d/celery.d/auto_conf_discovery.yaml:ro",
                    f"{DISCOVERY_HELPERS_DIR}:{SITE_PACKAGES}/datadog_checks/base/utils/discovery:ro",
                    f"{OPENMETRICS_V2_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/openmetrics/v2/base.py:ro",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                ],
            },
        )


@pytest.fixture(scope='session')
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)
