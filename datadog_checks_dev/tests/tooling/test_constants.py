# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.dev.tooling.constants import (
    get_agent_release_requirements, get_agent_requirements, get_root, set_root
)


def test_get_agent_release_requirements():
    with mock.patch('datadog_checks.dev.tooling.constants.get_root', return_value='/'):
        assert get_agent_release_requirements() == '/requirements-agent-release.txt'


def test_get_agent_requirements():
    with mock.patch('datadog_checks.dev.tooling.constants.get_root', return_value='/'):
        assert get_agent_requirements() == '/datadog_checks_base/datadog_checks/base/data/agent_requirements.in'


def test_get_root():
    assert get_root() == ''
    set_root('foo')
    assert get_root() == 'foo'
