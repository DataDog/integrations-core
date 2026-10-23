# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import json
import logging
import os
from pathlib import Path
from urllib.request import urlopen

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.go_expvar import GoExpvar

from . import common

log = logging.getLogger(__file__)


@pytest.fixture
def go_expvar_mock(fake_http, fake_http_response):
    filepath = Path(common.HERE) / 'fixtures' / 'expvar_output'
    fake_http_response(common.URL_WITH_PATH, json_data=json.loads(filepath.read_bytes()))
    yield
    fake_http.assert_all_responses_consumed()


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up a simple container that contains a simple go expvar app
    """

    with docker_run(os.path.join(common.HERE, 'compose', 'docker-compose.yaml'), endpoints=[common.URL]):
        for _ in range(9):
            with urlopen(common.URL + '?user=123456', timeout=10):
                pass
        yield common.INSTANCE


@pytest.fixture
def check():
    return GoExpvar(common.CHECK_NAME, {}, [common.INSTANCE])
