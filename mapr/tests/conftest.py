# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock
import pytest

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield


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
                msg = mock.MagicMock(error=lambda: None, value=lambda: line)
                yield msg
            yield None

    poll = mock.MagicMock(side_effect=messages_iter())
    with mock.patch('datadog_checks.mapr.mapr.MaprCheck.get_connection', return_value=mock.MagicMock(poll=poll)):
        yield
