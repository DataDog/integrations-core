# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import subprocess
import time
from contextlib import suppress
from typing import Any, Iterator

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from . import common

WORKFLOW_OK_PATH = '/workflows/sample_workflow.json'
WORKFLOW_FAIL_PATH = '/workflows/sample_workflow_failing.json'
WORKFLOW_OK_ID = 'testWorkflowOk'
WORKFLOW_FAIL_ID = 'testWorkflowFail'

WEBHOOK_OK_PATH = '/webhook/test'
WEBHOOK_FAIL_PATH = '/webhook/fail'

CONTAINER = 'n8n-test'


def _docker_exec(*cmd: str) -> str:
    return subprocess.check_output(['docker', 'exec', CONTAINER, *cmd], stderr=subprocess.STDOUT).decode()


def _wait_for_n8n(timeout: int = 90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with suppress(requests.RequestException):
            if requests.get(common.MAIN_INSTANCE['openmetrics_endpoint'], timeout=2).status_code == 200:
                return
        time.sleep(2)
    raise RuntimeError('n8n did not become healthy in time')


def _activate_imported_workflows():
    """Import sample workflows by stable id, activate them, restart n8n so webhooks register."""
    _docker_exec('n8n', 'import:workflow', f'--input={WORKFLOW_OK_PATH}')
    _docker_exec('n8n', 'import:workflow', f'--input={WORKFLOW_FAIL_PATH}')

    for wf_id in (WORKFLOW_OK_ID, WORKFLOW_FAIL_ID):
        _docker_exec('n8n', 'update:workflow', f'--id={wf_id}', '--active=true')

    subprocess.check_call(['docker', 'restart', CONTAINER], stderr=subprocess.STDOUT)
    _wait_for_n8n()


def _generate_workflow_traffic(iterations: int = 5):
    """Trigger workflows + API endpoints so workflow event and HTTP histogram metrics fire.

    Failures are not silently swallowed — at least the OK webhook must respond, otherwise
    the test fixture is broken and downstream metric assertions can't be trusted.
    """
    base_url = f'http://{common.HOST}:{common.MAIN_PORT}'
    api_paths = ('/healthz', '/healthz/readiness', '/rest/login')
    ok_responses = 0
    for _ in range(iterations):
        with suppress(requests.RequestException):
            ok = requests.get(f'{base_url}{WEBHOOK_OK_PATH}', timeout=5)
            if ok.status_code < 500:
                ok_responses += 1
        # Webhook fail is *expected* to error out — that's the point of triggering it.
        for path in (WEBHOOK_FAIL_PATH, *api_paths):
            with suppress(requests.RequestException):
                requests.get(f'{base_url}{path}', timeout=5)
    if ok_responses == 0:
        raise RuntimeError('Test webhook returned no successful responses; workflow registration failed')


def _wait_for_workflow_metric(timeout: int = 30):
    """Poll /metrics until at least one workflow_started_total sample is non-zero."""
    deadline = time.monotonic() + timeout
    metrics_url = common.MAIN_INSTANCE['openmetrics_endpoint']
    while time.monotonic() < deadline:
        with suppress(requests.RequestException):
            payload = requests.get(metrics_url, timeout=3).text
            for line in payload.splitlines():
                if line.startswith('n8n_workflow_started_total') and not line.endswith(' 0'):
                    return
        time.sleep(2)
    raise RuntimeError('workflow_started_total never went non-zero')


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    conditions = [
        CheckEndpoints(common.MAIN_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(common.WORKER_INSTANCE['openmetrics_endpoint']),
        _activate_imported_workflows,
        _generate_workflow_traffic,
        _wait_for_workflow_metric,
    ]
    with docker_run(common.COMPOSE_FILE, conditions=conditions, env_vars=common.get_compose_env_vars()):
        config = {'instances': [common.MAIN_INSTANCE, common.WORKER_INSTANCE]}
        yield config, common.E2E_METADATA


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(common.MAIN_INSTANCE)


@pytest.fixture
def worker_instance() -> dict[str, Any]:
    return copy.deepcopy(common.WORKER_INSTANCE)
