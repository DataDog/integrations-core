# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import get_here

HERE = get_here()

# Cache for loaded fixtures to avoid repeated file reads
_fixture_cache = {}


def load_fixture(filename):
    """Load a JSON fixture file and return its content as a dictionary."""
    if filename in _fixture_cache:
        return _fixture_cache[filename]

    fixture_path = os.path.join(HERE, 'fixtures', filename)
    with open(fixture_path, 'r') as f:
        data = json.load(f)
        _fixture_cache[filename] = data
        return data


def load_fixture_page(filename, page):
    """Load a specific page from a consolidated fixture file.

    The fixture file should be a JSON array where each element is a page response.
    """
    pages = load_fixture(filename)
    if page < len(pages):
        return pages[page]
    # Return empty response for pages beyond available data
    return {"data": [], "metadata": {"totalAvailableResults": 0}}


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
    "page_limit": 50,
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
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        # Check if URL has pagination parameters
        page = None

        # Extract pagination from params dict
        if params:
            page = params.get('$page')

        # Extract pagination from URL query string
        if page is None and '?' in url:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if '$page' in query_params:
                page = int(query_params['$page'][0])

        # Default to page 0
        if page is None:
            page = 0

        # Health check endpoint
        if '/console' in url:
            return mock_resp

        # Host stats endpoint - always non-paginated
        if (
            "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts/71877eae-8fc1-4aae-8d20-70196dfb2f8d"
            in url
        ):
            response_data = load_fixture(
                "host_stats_0006411c-0286-bc71-9f02-191e334d457b_71877eae-8fc1-4aae-8d20-70196dfb2f8d.json"
            )
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Cluster stats endpoint - always non-paginated
        if "/api/clustermgmt/v4.0/stats/clusters/0006411c-0286-bc71-9f02-191e334d457b" in url:
            response_data = load_fixture("cluster_stats_0006411c-0286-bc71-9f02-191e334d457b.json")
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Hosts endpoint for cluster b6d83094 - paginated
        if '/api/clustermgmt/v4.0/config/clusters/b6d83094-9404-48de-9c74-ca6bddc3a01d/hosts' in url:
            response_data = load_fixture_page("hosts_b6d83094.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            mock_resp.status_code = 400
            return mock_resp

        # Hosts endpoint for cluster 0006411c - paginated
        if '/api/clustermgmt/v4.0/config/clusters/0006411c-0286-bc71-9f02-191e334d457b/hosts' in url:
            response_data = load_fixture_page("hosts_0006411c.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Clusters endpoint - paginated
        if '/api/clustermgmt/v4.0/config/clusters' in url:
            response_data = load_fixture_page("clusters.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # VM stats endpoint - paginated
        if 'api/vmm/v4.0/ahv/stats/vms' in url:
            response_data = load_fixture_page("vms_stats.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # VMs config endpoint - paginated
        if 'api/vmm/v4.0/ahv/config/vms' in url:
            response_data = load_fixture_page("vms.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Events endpoint - paginated
        if 'api/monitoring/v4.0/serviceability/events' in url:
            response_data = load_fixture_page("events.json", page)

            # Apply time filter if present (e.g., "creationTime gt 2026-01-02T14:35:00Z")
            filter_param = params.get('$filter', '') if params else ''
            if 'creationTime gt' in filter_param:
                from datetime import datetime

                # Extract the timestamp from filter
                filter_time_str = filter_param.split('creationTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                # Filter events by creationTime
                filtered_data = []
                for event in response_data.get('data', []):
                    event_time_str = event.get('creationTime', '')
                    if event_time_str:
                        event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                        if event_time > filter_time:
                            filtered_data.append(event)

                # Sort by creationTime asc (as specified by $orderBy param)
                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('creationTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Audits endpoint - paginated
        if 'api/monitoring/v4.0/serviceability/audits' in url:
            response_data = load_fixture_page("audits.json", page)

            # Apply time filter if present (e.g., "creationTime gt 2026-01-02T14:35:00Z")
            filter_param = params.get('$filter', '') if params else ''
            if 'creationTime gt' in filter_param:
                from datetime import datetime

                # Extract the timestamp from filter
                filter_time_str = filter_param.split('creationTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                # Filter audits by creationTime
                filtered_data = []
                for audit in response_data.get('data', []):
                    audit_time_str = audit.get('creationTime', '')
                    if audit_time_str:
                        audit_time = datetime.fromisoformat(audit_time_str.replace('Z', '+00:00'))
                        if audit_time > filter_time:
                            filtered_data.append(audit)

                # Sort by creationTime asc (as specified by $orderBy param)
                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('creationTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Tasks endpoint - paginated with time filtering and ordering
        if 'api/prism/v4.0/config/tasks' in url:
            response_data = load_fixture_page("tasks.json", page)

            # Apply time filter if present (e.g., "createdTime gt 2026-01-02T14:35:00Z")
            filter_param = params.get('$filter', '') if params else ''
            if 'createdTime gt' in filter_param:
                from datetime import datetime

                # Extract the timestamp from filter
                filter_time_str = filter_param.split('createdTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                # Filter tasks by createdTime
                filtered_data = []
                for task in response_data.get('data', []):
                    task_time_str = task.get('createdTime', '')
                    if task_time_str:
                        task_time = datetime.fromisoformat(task_time_str.replace('Z', '+00:00'))
                        if task_time > filter_time:
                            filtered_data.append(task)

                # Sort by createdTime asc (as specified by $orderBy param)
                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('createdTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Default response for unmapped URLs - return HTTP error
        print(f"[MOCK ERROR] No matching endpoint for URL: {url}")
        mock_resp.status_code = 404
        mock_resp.raise_for_status = mocker.Mock(side_effect=Exception("404 Not Found"))
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
