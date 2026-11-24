# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.base.utils import tagging
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(common.MOCKED_INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.MOCKED_INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)


@pytest.fixture
def allow_service_tag(monkeypatch):
    # The AWS SDK metrics of Karpenter have a `service` label that holds the AWS service.
    # Datadog reserves that tag name for the service of the monitored application.
    # Renaming the label changes the tags that customers receive, so it needs a change of its own.
    # Until then, this tag is the only generic tag name that the tests accept.
    monkeypatch.setattr(tagging, 'GENERIC_TAGS', tagging.GENERIC_TAGS - {'service'})
