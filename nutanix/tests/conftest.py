# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckEndpoints

HERE = get_here()
HOST = get_docker_hostname()
DOCKER_DIR = os.path.join(HERE, 'docker')

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

# Real Nutanix instance configuration
# Configure /etc/hosts to map nutanix.local to your Prism Central IP:
#   echo "<PRISM_CENTRAL_IP>  nutanix.local" | sudo tee -a /etc/hosts
AWS_INSTANCE = {
    "pc_ip": "https://nutanix.local",
    "pc_port": 9440,
    "pc_username": "dd_agent",
    "pc_password": "DummyPassw0rd!",
    "tls_verify": False,
    "page_limit": 50,
}


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up Docker container with Flask server serving Nutanix API fixtures.
    Set USE_NUTANIX_AWS=true env var to run against real AWS environment instead.
    """
    if os.environ.get('USE_NUTANIX_AWS'):
        # Use real AWS environment
        yield AWS_INSTANCE.copy()
    else:
        # Use Docker-based mock environment
        compose_file = os.path.join(DOCKER_DIR, 'docker-compose.yaml')

        conditions = [
            CheckEndpoints(f'http://{HOST}:9440/console', attempts=60, wait=1),
        ]

        with docker_run(
            compose_file=compose_file,
            service_name='nutanix-prism-central',
            conditions=conditions,
        ):
            instance = {
                "pc_ip": f"http://{HOST}",
                "pc_port": 9440,
                "pc_username": "admin",
                "pc_password": "secret",
                "tls_verify": False,
                "page_limit": 2,  # Use limit=2 to match paginated fixtures
            }
            yield instance


@pytest.fixture
def instance(dd_environment):
    """
    Returns instance config from dd_environment.
    This will be Docker config by default, or AWS config if USE_NUTANIX_AWS=true.
    """
    return dd_environment.copy()


@pytest.fixture
def aws_instance():
    """Returns AWS instance config (for backward compatibility)."""
    return AWS_INSTANCE.copy()


@pytest.fixture
def mock_instance():
    """Returns mock instance config for unit tests."""
    return INSTANCE.copy()


@pytest.fixture
def mock_http_get(mocker):
    def mock_response(url, params=None, *args, **kwargs):
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = mocker.Mock()

        page = None

        if params:
            page = params.get('$page')

        if page is None and '?' in url:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if '$page' in query_params:
                page = int(query_params['$page'][0])

        if page is None:
            page = 0

        if '/console' in url:
            return mock_resp

        if (
            "/api/clustermgmt/v4.0/stats/clusters/00064715-c043-5d8f-ee4b-176ec875554d/hosts/d8787814-4fe8-4ba5-931f-e1ee31c294a6"
            in url
        ):
            response_data = load_fixture("host_stats_00064715_d8787814.json")
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if "/api/clustermgmt/v4.0/stats/clusters/00064715-c043-5d8f-ee4b-176ec875554d" in url:
            response_data = load_fixture("cluster_stats_00064715.json")
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters/d07db284-6df6-4ca2-88cd-9dd5ed71ac08/hosts' in url:
            mock_resp.status_code = 400
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters/00064715-c043-5d8f-ee4b-176ec875554d/hosts' in url:
            response_data = load_fixture_page("hosts_00064715.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if '/api/clustermgmt/v4.0/config/clusters' in url:
            response_data = load_fixture_page("clusters.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if '/api/prism/v4.0/config/categories' in url:
            response_data = load_fixture_page("categories.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if 'api/vmm/v4.0/ahv/stats/vms' in url:
            response_data = load_fixture_page("vms_stats.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if 'api/vmm/v4.0/ahv/config/vms' in url:
            response_data = load_fixture_page("vms.json", page)
            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        # Events endpoint - paginated
        if 'api/monitoring/v4.0/serviceability/events' in url:
            response_data = load_fixture_page("events.json", page)

            filter_param = params.get('$filter', '') if params else ''
            if 'creationTime gt' in filter_param:
                from datetime import datetime

                filter_time_str = filter_param.split('creationTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                filtered_data = []
                for event in response_data.get('data', []):
                    event_time_str = event.get('creationTime', '')
                    if event_time_str:
                        event_time = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                        if event_time > filter_time:
                            filtered_data.append(event)

                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('creationTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if 'api/monitoring/v4.0/serviceability/audits' in url:
            response_data = load_fixture_page("audits.json", page)

            filter_param = params.get('$filter', '') if params else ''
            if 'creationTime gt' in filter_param:
                from datetime import datetime

                filter_time_str = filter_param.split('creationTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                filtered_data = []
                for audit in response_data.get('data', []):
                    audit_time_str = audit.get('creationTime', '')
                    if audit_time_str:
                        audit_time = datetime.fromisoformat(audit_time_str.replace('Z', '+00:00'))
                        if audit_time > filter_time:
                            filtered_data.append(audit)

                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('creationTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        if 'api/monitoring/v4.0/serviceability/alerts' in url or 'api/monitoring/v4.2/serviceability/alerts' in url:
            response_data = load_fixture_page("alerts.json", page)

            filter_param = params.get('$filter', '') if params else ''
            if 'creationTime gt' in filter_param:
                from datetime import datetime

                filter_time_str = filter_param.split('creationTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                filtered_data = []
                for alert in response_data.get('data', []):
                    alert_time_str = alert.get('creationTime', '')
                    if alert_time_str:
                        alert_time = datetime.fromisoformat(alert_time_str.replace('Z', '+00:00'))
                        if alert_time > filter_time:
                            filtered_data.append(alert)

                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('creationTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp
        if 'api/prism/v4.0/config/tasks' in url:
            response_data = load_fixture_page("tasks.json", page)

            filter_param = params.get('$filter', '') if params else ''
            if 'createdTime gt' in filter_param:
                from datetime import datetime

                filter_time_str = filter_param.split('createdTime gt ')[-1].strip()
                filter_time = datetime.fromisoformat(filter_time_str.replace('Z', '+00:00'))

                filtered_data = []
                for task in response_data.get('data', []):
                    task_time_str = task.get('createdTime', '')
                    if task_time_str:
                        task_time = datetime.fromisoformat(task_time_str.replace('Z', '+00:00'))
                        if task_time > filter_time:
                            filtered_data.append(task)

                filtered_data.sort(
                    key=lambda t: datetime.fromisoformat(t.get('createdTime', '').replace('Z', '+00:00'))
                )

                response_data = dict(response_data)
                response_data['data'] = filtered_data

            mock_resp.json = mocker.Mock(return_value=response_data)
            return mock_resp

        print(f"[MOCK ERROR] No matching endpoint for URL: {url}")
        mock_resp.status_code = 404
        mock_resp.raise_for_status = mocker.Mock(side_effect=Exception("404 Not Found"))
        return mock_resp

    return mocker.patch('requests.Session.get', side_effect=mock_response)
