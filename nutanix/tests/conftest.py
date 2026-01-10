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
    "page_limit": 2,  # Use limit=2 to match paginated fixtures
}

AWS_INSTANCE = {
    "pc_ip": "https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com",
    "pc_port": 9440,
    "pc_username": "dd_agent",
    "pc_password": "DummyPassw0rd!",
    "tls_verify": False,
    "page_limit": 2,  # Use limit=2 to match paginated fixtures
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
    def mock_response(url, params=None, *args, **kwargs):
        # Print request details for debugging
        print("\n" + "=" * 60)
        print(f"[MOCK REQUEST] URL: {url}")
        if params:
            print(f"[MOCK REQUEST] Params: {params}")
        else:
            print("[MOCK REQUEST] Params: None")
        print("=" * 60)

        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        # Check if URL has pagination parameters
        page = None
        limit = None

        # Extract pagination from params dict
        if params:
            page = params.get('$page')
            limit = params.get('$limit')

        # Extract pagination from URL query string
        if not page and not limit and '?' in url:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if '$page' in query_params:
                page = int(query_params['$page'][0])
            if '$limit' in query_params:
                limit = int(query_params['$limit'][0])

        # Print what was extracted
        # print(f"[MOCK EXTRACTED] Page: {page}, Limit: {limit}")

        # Health check endpoint
        if '/console' in url:
            # print("[MOCK RESPONSE] Health check endpoint")
            return mock_resp

        # Host stats endpoint - always non-paginated
        if (
            "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts/71877eae-8fc1-4aae-8d20-70196dfb2f8d"
            in url
        ):
            fixture_name = "host_stats_0006411c-0286-bc71-9f02-191e334d457b_71877eae-8fc1-4aae-8d20-70196dfb2f8d.json"
            # print(f"[MOCK LOADING] Fixture: {fixture_name}")
            response_data = load_fixture(fixture_name)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Cluster stats endpoint - always non-paginated
        if "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b" in url:
            fixture_name = "cluster_stats_0006411c-0286-bc71-9f02-191e334d457b.json"
            # print(f"[MOCK LOADING] Fixture: {fixture_name}")
            response_data = load_fixture(fixture_name)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Hosts endpoint for cluster b6d83094 - always paginated
        if '/api/clustermgmt/v4.0/config/clusters/b6d83094-9404-48de-9c74-ca6bddc3a01d/hosts' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"hosts_b6d83094-9404-48de-9c74-ca6bddc3a01d_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)

            mock_resp.json = mocker.Mock(return_value=response_data)
            mock_resp.status_code = 400
            return mock_resp

        # Hosts endpoint for cluster 0006411c - always paginated
        if '/api/clustermgmt/v4.0/config/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"hosts_0006411c-0286-bc71-9f02-191e334d457b_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Clusters endpoint - always paginated
        if '/api/clustermgmt/v4.0/config/clusters' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"clusters_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # VM stats endpoint - always paginated
        if 'api/vmm/v4.0/ahv/stats/vms' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"vms_stats_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # VMs config endpoint - always paginated
        if 'api/vmm/v4.0/ahv/config/vms' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"vms_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Events endpoint - always paginated
        if 'api/monitoring/v4.0/serviceability/events' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"events_limit{limit}_page{page}.json"
            # print(f"[MOCK LOADING] Paginated fixture: {paginated_fixture}")
            response_data = load_fixture(paginated_fixture)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Tasks endpoint - always paginated
        if 'api/prism/v4.0/config/tasks' in url:
            # Default to page 0, limit 2 if not specified
            if page is None:
                page = 0
            if limit is None:
                limit = 50

            paginated_fixture = f"tasks_limit{limit}_page{page}.json"
            response_data = load_fixture(paginated_fixture)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Default response for unmapped URLs - return HTTP error
        # print(f"[MOCK ERROR] No matching endpoint for URL: {url}")
        mock_resp.status_code = 404
        mock_resp.raise_for_status = mocker.Mock(side_effect=Exception("404 Not Found"))
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
