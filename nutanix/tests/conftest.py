# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

# Test instance configurations
AWS_INSTANCE = {
    "pc_ip": "prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com",
    "pc_port": 9440,
    "username": "admin",
    "password": "uyp2ZFW9qat4dxn-rza",
    "tls_verify": False,
}

MOCK_INSTANCE = {
    "pc_ip": "10.0.0.197",
    "pc_port": 9440,
    "username": "admin",
    "password": "secret",
}


@pytest.fixture(scope='session')
def dd_environment():
    """Datadog test environment fixture."""
    yield


@pytest.fixture
def instance():
    """Return a basic empty instance config."""
    return {}


@pytest.fixture
def mock_instance():
    """Return a mock instance config for unit tests."""
    return MOCK_INSTANCE.copy()


@pytest.fixture
def aws_instance():
    """Return AWS test instance config."""
    return AWS_INSTANCE.copy()


@pytest.fixture
def mock_http_get(mocker):
    """
    Mock HTTP GET requests and return JSON payloads from fixtures.

    This fixture automatically maps API endpoints to fixture files.
    """
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')

    def load_fixture(filename):
        """Load a fixture file."""
        fixture_path = os.path.join(fixtures_dir, filename)
        try:
            with open(fixture_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return empty data if fixture doesn't exist
            return {"data": []}

    def mock_response(url, *args, **kwargs):
        """Create a mock response based on the URL."""
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        # Map URLs to fixture files
        if '/console' in url:
            # Health check endpoint - just return success
            return mock_resp

        elif '/api/clustermgmt/v4.0/config/clusters' in url and '/stats/' not in url:
            # Clusters list endpoint
            data = load_fixture('clusters.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/clustermgmt/v4.0/stats/clusters/' in url:
            # Cluster stats endpoint
            data = load_fixture('cluster_stats.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/clustermgmt/v4.0/config/storage-containers' in url:
            # Storage containers endpoint
            data = load_fixture('storage_containers.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/clustermgmt/v4.0/config/hosts' in url and '/stats/' not in url:
            # Hosts list endpoint
            data = load_fixture('hosts.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/clustermgmt/v4.0/stats/hosts/' in url:
            # Host stats endpoint
            data = load_fixture('host_stats.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/vmm/v4.0/content/vms' in url and '/stats/' not in url:
            # VMs list endpoint
            data = load_fixture('vms.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/vmm/v4.0/ahv/stats/vms/' in url:
            # VM stats endpoint
            data = load_fixture('vm_stats.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/prism/v4.0/config/events' in url:
            # Events endpoint
            data = load_fixture('events.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        elif '/api/prism/v4.0/config/alerts' in url:
            # Alerts endpoint
            data = load_fixture('alerts.json')
            mock_resp.json = mocker.Mock(return_value=data)
            return mock_resp

        # Default response for unmapped URLs
        mock_resp.json = mocker.Mock(return_value={"data": []})
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
