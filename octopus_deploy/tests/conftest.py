# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.fs import get_here

from .constants import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_OCTOPUS_LAB

PARAMS_TO_FILENAME_MAPPING = {
    # space-wide queued/executing tasks
    'name=Deploy/states=Queued,Executing/skip=0/take=2': 'space_in_progress_low_limit_pg1',
    'name=Deploy/states=Queued,Executing/skip=0/take=30': 'space_in_progress_high_limit_pg1',
    'name=Deploy/states=Queued,Executing/skip=0/take=300': 'space_in_progress_high_limit_pg1',
    # space-wide tasks completed in an empty window (the first run of a check)
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=2': 'space_none_completed_low_limit_pg1',
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=30': 'space_none_completed_high_limit_pg1',
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:00.123000+00:00/skip=0/take=300': 'space_none_completed_high_limit_pg1',
    # space-wide tasks completed during the collection interval
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=2': 'space_completed_low_limit_pg1',
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=2/take=2': 'space_completed_low_limit_pg2',
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=30': 'space_completed_high_limit_pg1',
    'name=Deploy/fromCompletedDate=2024-09-23 14:45:00.123000+00:00/'
    'toCompletedDate=2024-09-23 14:45:15.123000+00:00/skip=0/take=300': 'space_completed_high_limit_pg1',
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
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:15.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=300': 'events_high_limit_pg1',
    'from=2024-09-23 14:45:00.123000+00:00/to=2024-09-23 14:45:00.123000+00:00/'
    'eventCategories=MachineHealthy,MachineUnhealthy,MachineUnavailable,CertificateExpired,DeploymentFailed,'
    'DeploymentSucceeded,LoginFailed,MachineAdded,MachineDeleted/skip=0/take=300': 'no_events_high_limit_pg1',
    # the rest of the paginated endpoints
    'skip=0/take=2': 'low_limit_pg1',
    'skip=2/take=2': 'low_limit_pg2',
    'skip=0/take=30': 'high_limit_pg1',
    'skip=0/take=300': 'high_limit_pg1',
}

# Endpoints the check reads in bulk with `?ids=`, mocked from the per-id fixtures of the same collection.
BULK_ID_ENDPOINTS = ('deployments',)


class OctopusEmulatorHTTPClient(FakeHTTPClient):
    """Suite-local Octopus API emulator. Responses depend on request params and time windows, and the caching tests
    need many check runs, which explicit per-request registration cannot express."""

    def __init__(self, resolve, http_error, mock_data, elapsed_total_seconds):
        super().__init__()
        self._resolve = resolve
        self._http_error = http_error
        self._mock_data = mock_data
        self._elapsed_total_seconds = elapsed_total_seconds

    def get(self, url, **options):
        self.register_response('GET', url, self._emulate(get_url_path(url), options))
        return super().get(url, **options)

    def _emulate(self, path, options):
        if path in self._http_error:
            return self._http_error[path]
        if path in self._mock_data:
            return json_response(self._mock_data[path])
        try:
            json_data = self._resolve('GET', path, headers=options.get('headers'), params=options.get('params'))
        except HTTPClientStatusError as e:
            return e
        return json_response(json_data, elapsed=timedelta(seconds=self._elapsed_total_seconds.get(path, 0.0)))


def json_response(json_data, **kwargs):
    return FakeHTTPResponse(content=json.dumps(json_data).encode(), json_result=json_data, **kwargs)


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


def get_url_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path


@pytest.fixture
def mock_responses():
    responses_map = {}

    def process_files(dir, response_parent):
        for file in dir.rglob('*'):
            if file.is_file() and file.stem != ".slash":
                relative_dir_path = (
                    "/" + str(file.parent.relative_to(dir)) + ("/" if (file.parent / ".slash").is_file() else "")
                )
                if relative_dir_path not in response_parent:
                    response_parent[relative_dir_path] = {}
                json_data = get_json_value_from_file(file)
                response_parent[relative_dir_path][file.stem] = json_data

    def process_dir(dir, response_parent):
        response_parent[dir.name] = {}
        process_files(dir, response_parent[dir.name])

    def create_responses_tree():
        root_dir_path = os.path.join(get_here(), 'fixtures')
        method_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name in ['GET', 'POST']]
        for method_subdir in method_subdirs:
            process_dir(method_subdir, responses_map)

    def bulk_by_ids(method, request_path, ids):
        """Emulate the Octopus `?ids=` collection filter using the individual per-id fixtures."""
        items = []
        for item_id in ids:
            item = responses_map.get(method, {}).get(f'{request_path}/{item_id}', {}).get('response')
            if item is not None:
                items.append(item)
        return {
            'Items': items,
            'TotalResults': len(items),
            'ItemsPerPage': len(items),
            'NumberOfPages': 1,
            'LastPageNumber': 0,
        }

    def method(method, url, file='response', headers=None, params=None):
        filename = file
        request_path = url
        request_path = request_path.replace('?', '/')
        if params and params.get('ids') is not None and request_path.split('/')[-1] in BULK_ID_ENDPOINTS:
            return bulk_by_ids(method, request_path, params['ids'])
        if params:
            param_string = ""
            for key, val in params.items():
                if type(val) is list:
                    val_string = ','.join(f'{str(val_item)}' for val_item in val)
                else:
                    val_string = str(val)
                param_string += ("/" if param_string else "") + f'{key}={val_string}'

            filename = PARAMS_TO_FILENAME_MAPPING.get(param_string)
            print(f"param string: {param_string}")

        print(f"request path: {request_path}/{filename}")
        response = responses_map.get(method, {}).get(request_path, {}).get(filename)
        return response

    create_responses_tree()
    yield method


@pytest.fixture
def mock_http_call(mock_responses):
    def call(method, url, file='response', headers=None, params=None):
        response = mock_responses(method, url, file=file, headers=headers, params=params)
        if response is not None:
            return response
        raise HTTPClientStatusError('404 Client Error', response=FakeHTTPResponse(status_code=404, url=url))

    yield call


@pytest.fixture
def mock_http_get(request, mocker, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    client = OctopusEmulatorHTTPClient(
        mock_http_call,
        http_error=param.pop('http_error', {}),
        mock_data=param.pop('mock_data', {}),
        elapsed_total_seconds=param.pop('elapsed_total_seconds', {}),
    )

    def create_client(check, *_args, **_kwargs):
        # Same guard as the fake_http fixture: the fake models the contract a check only gets by opting in.
        if not getattr(check, 'AGNOSTIC_HTTP_CLIENT', False):
            raise AssertionError(f'{type(check).__name__} must set AGNOSTIC_HTTP_CLIENT = True to use mock_http_get.')
        return client

    mocker.patch.object(AgentCheck, 'create_http_client', autospec=True, side_effect=create_client)
    return client
