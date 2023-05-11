# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.dev import EnvVars
from datadog_checks.dev.ci import running_on_ci, running_on_linux_ci, running_on_macos_ci, running_on_windows_ci


def test_running_on_windows_ci():
    with mock.patch.dict(os.environ, {'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI': 'url', 'AGENT_OS': 'Windows_NT'}):
        assert running_on_ci() is True
        assert running_on_windows_ci() is True


def test_running_on_linux_ci():
    with mock.patch.dict(os.environ, {'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI': 'url', 'AGENT_OS': 'Linux'}):
        assert running_on_ci() is True
        assert running_on_linux_ci() is True


def test_running_on_macos_ci():
    with mock.patch.dict(os.environ, {'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI': 'url', 'AGENT_OS': 'Darwin'}):
        assert running_on_ci() is True
        assert running_on_macos_ci() is True


def test_not_running_ci():
    with EnvVars(ignore=['GITHUB_ACTIONS', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI']):
        with mock.patch.dict(os.environ, {'AGENT_OS': 'Linux'}):
            assert running_on_ci() is False
            assert running_on_linux_ci() is False
