# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Iterator

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from . import common

# Test webhook paths (only the test-fixture workflows expose these; the lab workflows
# expose /webhook/lab/* paths and are exercised by the lab traffic generator instead).
WEBHOOK_OK_PATH = '/webhook/test'
WEBHOOK_FAIL_PATH = '/webhook/fail'

CONTAINER = 'n8n-test'

# Directories whose ``*.json`` workflow files are bind-mounted into the container.
# In test mode only the two test fixtures are mounted at ``/workflows/``;
# in lab mode the lab compose mounts both the test fixtures and the lab workflows.
_TEST_WORKFLOW_DIR = Path(common.HERE) / 'docker'
_LAB_WORKFLOW_DIR = Path(common.HERE) / 'lab' / 'workflows'


def _docker_exec(*cmd: str) -> str:
    return subprocess.check_output(['docker', 'exec', CONTAINER, *cmd], stderr=subprocess.STDOUT).decode()


def _wait_for_n8n(timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if requests.get(f'http://{common.HOST}:{common.MAIN_PORT}/healthz', timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError('n8n did not become healthy in time')


def _workflow_files() -> list[Path]:
    """Return every workflow JSON file that the active compose mounts into the container.

    The lab compose mounts both the test fixtures and the lab workflows under ``/workflows/``;
    the test compose mounts only the two test fixtures.
    """
    files = sorted(_TEST_WORKFLOW_DIR.glob('sample_workflow*.json'))
    if common.IS_LAB:
        files += sorted(_LAB_WORKFLOW_DIR.glob('lab_*.json'))
    return files


def _workflow_id(path: Path) -> str:
    return json.loads(path.read_text())['id']


def _activate_imported_workflows() -> None:
    """Import all bind-mounted workflows by stable id, activate them, restart n8n so webhooks register."""
    for path in _workflow_files():
        _docker_exec('n8n', 'import:workflow', f'--input=/workflows/{path.name}')
        _docker_exec('n8n', 'update:workflow', f'--id={_workflow_id(path)}', '--active=true')

    subprocess.check_call(
        ['docker', 'compose', '-f', common.COMPOSE_FILE, 'restart', 'n8n'],
        stderr=subprocess.STDOUT,
    )
    _wait_for_n8n()


def _generate_workflow_traffic(iterations: int = 5) -> None:
    """Trigger the test webhooks + a few API endpoints so workflow / HTTP histogram metrics fire.

    Lab mode skips this — the lab traffic generator owns traffic generation and runs much
    longer / richer mixes than the integration tests need.
    """
    if common.IS_LAB:
        return

    base_url = f'http://{common.HOST}:{common.MAIN_PORT}'
    api_paths = ('/healthz', '/healthz/readiness', '/rest/login')
    ok_responses = 0
    for _ in range(iterations):
        try:
            ok = requests.get(f'{base_url}{WEBHOOK_OK_PATH}', timeout=5)
            if ok.status_code < 500:
                ok_responses += 1
        except requests.RequestException:
            pass
        # Webhook fail is *expected* to error out — that's the point of triggering it.
        for path in (WEBHOOK_FAIL_PATH, *api_paths):
            try:
                requests.get(f'{base_url}{path}', timeout=5)
            except requests.RequestException:
                pass
    if ok_responses == 0:
        raise RuntimeError('Test webhook returned no successful responses; workflow registration failed')


def _wait_for_workflow_metric(timeout: int = 30) -> None:
    """Poll /metrics until at least one workflow_started_total sample is non-zero.

    Lab mode skips this since traffic only starts after ``hatch run lab:generate``.
    """
    if common.IS_LAB:
        return

    deadline = time.monotonic() + timeout
    metrics_url = common.MAIN_INSTANCE['openmetrics_endpoint']
    while time.monotonic() < deadline:
        try:
            payload = requests.get(metrics_url, timeout=3).text
            for line in payload.splitlines():
                if line.startswith('n8n_workflow_started_total') and not line.endswith(' 0'):
                    return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError('workflow_started_total never went non-zero')


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[Any]:
    conditions = [
        CheckEndpoints(common.MAIN_INSTANCE['openmetrics_endpoint']),
        CheckEndpoints(common.WORKER_INSTANCE['openmetrics_endpoint']),
    ]
    instances = {'instances': [common.MAIN_INSTANCE, common.WORKER_INSTANCE]}
    with docker_run(common.COMPOSE_FILE, conditions=conditions, env_vars=common.get_compose_env_vars()):
        _activate_imported_workflows()
        _generate_workflow_traffic()
        _wait_for_workflow_metric()
        if common.IS_LAB:
            lab_config = copy.deepcopy(instances)
            lab_config['logs'] = [
                {
                    'type': 'file',
                    'path': '/n8n-event-logs/n8nEventLog*.log',
                    'source': 'n8n',
                    'service': 'n8n-event-bus',
                },
            ]
            # Lab mode: mount Docker state for stdout autodiscovery and the n8n data
            # volume for event-bus file logs.
            yield (
                lab_config,
                {
                    'docker_volumes': [
                        '/var/run/docker.sock:/var/run/docker.sock:ro',
                        '/var/lib/docker/containers:/var/lib/docker/containers:ro',
                        '/opt/datadog-agent/run:/opt/datadog-agent/run:rw',
                        'n8n_lab_data:/n8n-event-logs:ro',
                    ],
                },
            )
        else:
            yield instances


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(common.MAIN_INSTANCE)


@pytest.fixture
def worker_instance() -> dict[str, Any]:
    return copy.deepcopy(common.WORKER_INSTANCE)
