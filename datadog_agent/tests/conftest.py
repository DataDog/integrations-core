# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Iterator

import pytest

from datadog_checks.base.types import InstanceType
from datadog_checks.dev.utils import find_free_port

INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:5000/telemetry',
    'tags': ['test:tag'],
}


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[tuple[InstanceType, dict[str, Any]]]:
    # The check scrapes the telemetry endpoint of the E2E Agent it runs in, so no extra services are needed. That
    # Agent uses the host network, so serve its telemetry on a free port rather than the default 5000, which an
    # Agent installed on the host would already be listening on.
    port = find_free_port('127.0.0.1')
    instance = {**INSTANCE, 'openmetrics_endpoint': f'http://localhost:{port}/telemetry'}
    yield instance, {'env_vars': {'DD_EXPVAR_PORT': str(port)}}


@pytest.fixture
def instance() -> InstanceType:
    return INSTANCE.copy()
