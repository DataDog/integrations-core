# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.utils import running_on_windows_ci

not_windows_ci = pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')

HERE = get_here()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')
CHECK_NAME = 'mesos_slave'
URL = 'http://{}:5051'.format(get_docker_hostname())

MESOS_SLAVE_VERSION = '1.7.1'

INSTANCE = {'url': URL, 'tasks': ['hello'], 'tags': ['instance:mytag1']}

BAD_INSTANCE = {'url': 'http://localhost:9999', 'tasks': ['hello']}

PARAMETERS = 'test_case_name, request_mock_effects, expected_tags, expect_exception, expected_status'
