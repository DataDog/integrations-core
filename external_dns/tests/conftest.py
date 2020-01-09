# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from .common import FIXTURE_DIR


@pytest.fixture
def mock_external_dns():
    f_name = os.path.join(FIXTURE_DIR, 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()

    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split('\n'), headers={'Content-Type': 'text/plain'}
        ),
    ):
        yield


@pytest.fixture
def instance():
    return {'prometheus_url': 'http://localhost:7979/metrics', 'tags': ['custom:tag']}
