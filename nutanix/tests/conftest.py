# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import get_here

HERE = get_here()


def load_fixture(filename):
    """Load a JSON fixture file and return its content as a dictionary."""
    fixture_path = os.path.join(HERE, 'fixtures', filename)
    with open(fixture_path, 'r') as f:
        return json.load(f)


# Test instance configurations
INSTANCE = {
    "pc_ip": "10.0.0.197",
    "pc_port": 9440,
    "pc_username": "admin",
    "pc_password": "secret",
    "tls_verify": False,
}

AWS_INSTANCE = {
    "pc_ip": "https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com",
    "pc_port": 9440,
    "pc_username": "dd_agent_viewer",
    "pc_password": "DummyP4ssw0rd!",
    "tls_verify": False,
}


@pytest.fixture(scope="session")
def dd_environment():
    yield AWS_INSTANCE.copy()


@pytest.fixture
def aws_instance():
    return AWS_INSTANCE.copy()


@pytest.fixture
def mock_instance():
    return INSTANCE.copy()


@pytest.fixture
def mock_http_get(mocker):
    def mock_response(url, *args, **kwargs):
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        # Health check endpoint
        if '/console' in url:
            return mock_resp

        if (
            "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts/71877eae-8fc1-4aae-8d20-70196dfb2f8d"
            in url
        ):
            host_stats = load_fixture(
                "host_stats_0006411c-0286-bc71-9f02-191e334d457b_71877eae-8fc1-4aae-8d20-70196dfb2f8d.json"
            )
            mock_resp.json = mocker.Mock(return_value=host_stats)
            return mock_resp

        if "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b" in url:
            cluster_stats = load_fixture("cluster_stats_0006411c-0286-bc71-9f02-191e334d457b.json")
            mock_resp.json = mocker.Mock(return_value=cluster_stats)
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters/b6d83094-9404-48de-9c74-ca6bddc3a01d/hosts' in url:
            clusters_data = load_fixture("hosts_b6d83094-9404-48de-9c74-ca6bddc3a01d.json")
            mock_resp.json = mocker.Mock(return_value=clusters_data)
            mock_resp.status_code = 400
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts' in url:
            clusters_data = load_fixture("hosts_0006411c-0286-bc71-9f02-191e334d457b.json")
            mock_resp.json = mocker.Mock(return_value=clusters_data)
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters' in url:
            clusters_data = load_fixture("clusters.json")
            mock_resp.json = mocker.Mock(return_value=clusters_data)
            return mock_resp

        if 'api/vmm/v4.0/ahv/stats/vms/' in url:
            all_vm_stats = load_fixture("vms_stats.json")
            mock_resp.json = mocker.Mock(return_value=all_vm_stats)
            return mock_resp

        if 'api/vmm/v4.0/ahv/config/vms' in url:
            vms_data = load_fixture("vms.json")
            mock_resp.json = mocker.Mock(return_value=vms_data)
            return mock_resp

        # Default response for unmapped URLs - return HTTP error
        mock_resp.status_code = 404
        mock_resp.raise_for_status = mocker.Mock(side_effect=Exception("404 Not Found"))
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
