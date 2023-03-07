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
        'apt-get install -y gcc librdkafka-dev',
        'pip install setuptools',
        'pip install --global-option=build_ext --global-option="--library-dirs=/opt/mapr/lib"'
        ' --global-option="--include-dirs=/opt/mapr/include/" mapr-streams-python',
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
