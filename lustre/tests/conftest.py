# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import os
from os.path import isfile
from datadog_checks.dev import get_here


HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')


def mock_run_command(command_fixture_mapping):
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
    return {'node_type': 'client'}
