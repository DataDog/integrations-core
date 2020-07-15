# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest


@pytest.fixture
def instance():
    return {'prometheus_url': 'http://localhost:10055/metrics'}


@pytest.fixture()
def mock_get():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
