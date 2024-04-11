# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

from . import common

E2E_METADATA = {
    'post_install_commands': [
        'apt-get update',
        'apt-get install -y gcc gnupg lsb-release',
        "sh -c 'curl https://packages.confluent.io/deb/7.0/archive.key "
        "| gpg --dearmor -o /usr/share/keyrings/confluent.gpg'",
        "sh -c 'echo "
        "\"deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/confluent.gpg] "
        "https://packages.confluent.io/clients/deb $(lsb_release -cs) main\" "
        "> /etc/apt/sources.list.d/confluent.list'",
        'apt-get update',
        'apt-get install -y librdkafka-dev',
        '/opt/datadog-agent/embedded/bin/pip install mapr-streams-python',
    ]
}


@pytest.fixture(scope='session')
def dd_environment():
    yield common.INSTANCE, E2E_METADATA


@pytest.fixture
def instance():
    return deepcopy(common.INSTANCE)


@pytest.fixture
def mock_fqdn():
    with mock.patch('socket.getfqdn', return_value="stubbed.hostname"):
        yield


@pytest.fixture
def mock_ticket_file_readable():
    with mock.patch('os.access', return_value=True):
        yield


@pytest.fixture
def mock_getconnection():
    def messages_iter():
        with open(os.path.join(common.HERE, 'fixtures', 'metrics.txt'), 'r') as f:
            for line in f:
                msg = mock.MagicMock(error=lambda: None, value=lambda line=line: line)
                yield msg
            yield None

    poll = mock.MagicMock(side_effect=messages_iter())
    with mock.patch('datadog_checks.mapr.mapr.MaprCheck.get_connection', return_value=mock.MagicMock(poll=poll)):
        yield
