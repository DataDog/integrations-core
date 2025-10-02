# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from os.path import isfile

import mock
import pytest

from datadog_checks.dev import get_here
from datadog_checks.lustre import LustreCheck

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')


def _mock_run_command(command_fixture_mapping):
    def run_command(bin, *args, **kwargs):
        requested_command = f"{bin} {' '.join(args)}"
        for cmd, fixture in command_fixture_mapping.items():
            if requested_command.startswith(cmd):
                path = os.path.join(FIXTURES_DIR, fixture)
                if not isfile(path):
                    return fixture
                with open(path, 'r') as f:
                    return f.read()
        raise ValueError(f"Unexpected command: {requested_command}")

    return run_command


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {'node_type': 'client', "filesystems": ["lustre", "*"]}


@pytest.fixture
def mock_lustre_commands():
    """
    A fixture that provides a context manager for mocking LustreCheck._run_command.

    Usage:
        def test_something(mock_lustre_commands):
            mapping = {
                'lctl get_param -ny version': 'all_version.txt',
                'lctl dl': 'client_dl_yaml.txt',
            }
            with mock_lustre_commands(mapping):
                check = LustreCheck('lustre', {}, [instance])
                # test code here
    """

    def _mock_commands(command_fixture_mapping):
        return mock.patch.object(LustreCheck, '_run_command', side_effect=_mock_run_command(command_fixture_mapping))

    return _mock_commands
