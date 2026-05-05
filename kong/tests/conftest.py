# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run

from . import common

INTEGRATIONS_CORE_ROOT = Path(__file__).resolve().parents[2]
KONG_AUTOCONF = Path(__file__).parent.parent / "datadog_checks" / "kong" / "data" / "auto_conf_discovery.yaml"
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


@pytest.fixture(scope="session")
def dd_environment():
    """
    Start a kong cluster
    """
    with docker_run(
        compose_file=os.path.join(common.HERE, 'compose', 'docker-compose.yml'), endpoints=common.STATUS_URL
    ):
        yield (
            common.openmetrics_instance,
            {
                'docker_volumes': [
                    f"{KONG_AUTOCONF}:/etc/datadog-agent/conf.d/kong.d/auto_conf_discovery.yaml:ro",
                    f"{DISCOVERY_HELPERS_DIR}:{SITE_PACKAGES}/datadog_checks/base/utils/discovery:ro",
                    f"{OPENMETRICS_V2_BASE_PY}:{SITE_PACKAGES}/datadog_checks/base/checks/openmetrics/v2/base.py:ro",
                    "/var/run/docker.sock:/var/run/docker.sock:ro",
                ],
            },
        )


@pytest.fixture
def instance_openmetrics_v2():
    return common.openmetrics_instance
