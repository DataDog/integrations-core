# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

# Test instance configurations
MOCK_INSTANCE = {
    "pc_ip": "10.0.0.197",
    "pc_port": 9440,
    "pc_username": "admin",
    "pc_password": "secret",
    "pc_verify": False,
}


@pytest.fixture
def instance():
    return {}


@pytest.fixture
def mock_instance():
    return MOCK_INSTANCE.copy()


@pytest.fixture
def mock_http_get(mocker):
    def mock_response(url, *args, **kwargs):
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        # Health check endpoint
        if '/console' in url:
            return mock_resp

        # Default response for unmapped URLs
        mock_resp.json = mocker.Mock(return_value={"data": []})
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
