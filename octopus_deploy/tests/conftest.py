# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.fs import get_here

from .constants import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_OCTOPUS_LAB

PARAMS_TO_FILENAME_MAPPING = {
    # project 2 tasks
    'name=Deploy/project=Projects-1/states=Queued,Executing/skip=0/take=2': 'project_1_in_progress_low_limit_pg1',
    'name=Deploy/project=Projects-1/states=Queued,Executing/skip=0/take=30': 'project_1_in_progress_high_limit_pg1',
    'name=Deploy/project=Projects-1/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=2': 'project_1_none_completed_low_limit_pg1',
    'name=Deploy/project=Projects-1/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=30': 'project_1_none_completed_high_limit_pg1',
    'name=Deploy/project=Projects-1/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=2': 'project_1_completed_low_limit_pg1',
    'name=Deploy/project=Projects-1/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=30': 'project_1_completed_high_limit_pg1',
    # project 2 tasks
    'name=Deploy/project=Projects-2/states=Queued,Executing/skip=0/take=2': 'project_2_in_progress_low_limit_pg1',
    'name=Deploy/project=Projects-2/states=Queued,Executing/skip=0/take=30': 'project_2_in_progress_high_limit_pg1',
    'name=Deploy/project=Projects-2/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=2': 'project_2_none_completed_low_limit_pg1',
    'name=Deploy/project=Projects-2/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=30': 'project_2_none_completed_high_limit_pg1',
    'name=Deploy/project=Projects-2/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=2': 'project_2_completed_low_limit_pg1',
    'name=Deploy/project=Projects-2/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=30': 'project_2_completed_high_limit_pg1',
    # project 3 tasks
    'name=Deploy/project=Projects-3/states=Queued,Executing/skip=0/take=2': 'project_3_in_progress_low_limit_pg1',
    'name=Deploy/project=Projects-3/states=Queued,Executing/skip=0/take=30': 'project_3_in_progress_high_limit_pg1',
    'name=Deploy/project=Projects-3/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=2': 'project_3_none_completed_low_limit_pg1',
    'name=Deploy/project=Projects-3/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=30': 'project_3_none_completed_high_limit_pg1',
    'name=Deploy/project=Projects-3/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=2': 'project_3_completed_low_limit_pg1',
    'name=Deploy/project=Projects-3/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=2/take=2': 'project_3_completed_low_limit_pg2',
    'name=Deploy/project=Projects-3/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=30': 'project_3_completed_high_limit_pg1',
    # project 4 tasks
    'name=Deploy/project=Projects-4/states=Queued,Executing/skip=0/take=2': 'project_4_in_progress_low_limit_pg1',
    'name=Deploy/project=Projects-4/states=Queued,Executing/skip=0/take=30': 'project_4_in_progress_high_limit_pg1',
    'name=Deploy/project=Projects-4/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=2': 'project_4_none_completed_low_limit_pg1',
    'name=Deploy/project=Projects-4/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=30': 'project_4_none_completed_high_limit_pg1',
    'name=Deploy/project=Projects-4/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=2': 'project_4_completed_low_limit_pg1',
    'name=Deploy/project=Projects-4/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=30': 'project_4_completed_high_limit_pg1',
    # events
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:15.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=2': 'events_low_limit_pg1',
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:15.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=2/take=2': 'events_low_limit_pg2',
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:15.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=30': 'events_high_limit_pg1',
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:00.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=2': 'no_events_low_limit_pg1',
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:00.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=30': 'no_events_high_limit_pg1',
    # the rest of the paginated endpoints
    'skip=0/take=2': 'low_limit_pg1',
    'skip=2/take=2': 'low_limit_pg2',
    'skip=0/take=30': 'high_limit_pg1',
}


@pytest.fixture(scope='session')
def dd_environment():
    if USE_OCTOPUS_LAB:
        yield LAB_INSTANCE
    else:
        compose_file = COMPOSE_FILE
        endpoint = INSTANCE["octopus_endpoint"]
        conditions = [
            CheckDockerLogs(identifier='octopus-api', patterns=['server running']),
            CheckEndpoints(f'{endpoint}/api/spaces'),
        ]
        with docker_run(compose_file, conditions=conditions):
            yield INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def _parse_params(param_string):
    params = {}
    for item in param_string.split('/'):
        name, value = item.split('=', 1)
        if name in {'skip', 'take'}:
            params[name] = int(value)
        elif name in {'states', 'eventCategories'}:
            params[name] = value.split(',')
        elif name in {'fromCompletedDate', 'toCompletedDate', 'from', 'to'}:
            params[name] = datetime.fromisoformat(value)
        else:
            params[name] = value
    return params


FILENAME_TO_PARAMS = {
    filename: _parse_params(param_string) for param_string, filename in PARAMS_TO_FILENAME_MAPPING.items()
}


@pytest.fixture
def octopus_http(request, fake_http, fake_http_response):
    fixture_options = dict(getattr(request, 'param', None) or {})
    error_responses = fixture_options.get('http_error', {})
    data_responses = fixture_options.get('mock_data', {})
    elapsed_seconds = fixture_options.get('elapsed_total_seconds', {})

    for route, response in error_responses.items():
        for _ in range(10):
            fake_http.register_response('GET', f"{INSTANCE['octopus_endpoint']}{route}", response)
    for route, payload in data_responses.items():
        for _ in range(10):
            fake_http_response(f"{INSTANCE['octopus_endpoint']}{route}", json_data=payload)

    root = Path(get_here()) / 'fixtures' / 'GET'
    overridden_routes = set(error_responses) | set(data_responses)
    fixture_urls = set()
    for file in root.rglob('*.json'):
        route = '/' + str(file.parent.relative_to(root))
        if route in overridden_routes:
            continue
        params = FILENAME_TO_PARAMS.get(file.stem, {})
        url = f"{INSTANCE['octopus_endpoint']}{route}"
        fixture_urls.add(url)
        for _ in range(10):
            fake_http_response(
                url,
                json_data=get_json_value_from_file(file),
                match_options={'params': params},
                elapsed=timedelta(seconds=elapsed_seconds.get(route, 0.0)),
            )

    fallback_urls = fixture_urls | {
        f"{INSTANCE['octopus_endpoint']}/api/Spaces-2/environments",
        f"{INSTANCE['octopus_endpoint']}/api/Spaces-2/machines",
        f"{INSTANCE['octopus_endpoint']}/api/Spaces-1/deployments/Deployments-111",
        f"{INSTANCE['octopus_endpoint']}/api/Spaces-1/deployments/Deployments-118",
        f"{INSTANCE['octopus_endpoint']}/api/Spaces-1/releases/None",
    }
    for url in fallback_urls:
        for _ in range(50):
            fake_http_response(url, status_code=404)

    return fake_http
