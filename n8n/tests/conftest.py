# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import json
import subprocess
from contextlib import suppress
from pathlib import Path
from typing import Any, Iterator

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor

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


def _n8n_healthy() -> None:
    """WaitFor predicate: succeeds once /healthz returns 200, retries on connection errors or non-2xx."""
    requests.get(f'http://{common.HOST}:{common.MAIN_PORT}/healthz', timeout=2).raise_for_status()


def _test_webhook_registered() -> None:
    """WaitFor predicate: succeeds once /webhook/test responds non-404.

    After ``docker compose restart n8n`` the ``/healthz`` endpoint can be served before n8n has
    finished re-registering active workflows' webhook routes. On n8n 2.x that gap is wide enough
    to make ``_generate_workflow_traffic`` race the registration and observe a 404. Polling the
    webhook itself closes the race.
    """
    response = requests.get(f'http://{common.HOST}:{common.MAIN_PORT}{WEBHOOK_OK_PATH}', timeout=5)
    if response.status_code == 404:
        raise RuntimeError(f'Webhook {WEBHOOK_OK_PATH} not yet registered (status 404)')


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
    """Import all bind-mounted workflows by stable id, activate them, restart n8n so webhooks register.

    Used as a ``docker_run`` condition. The earlier ``CheckEndpoints`` conditions guarantee n8n is
    booted before we issue CLI commands; the internal ``WaitFor(_n8n_healthy)`` re-waits for n8n
    after the restart so the next condition runs against a live process.
    """
    for path in _workflow_files():
        _docker_exec('n8n', 'import:workflow', f'--input=/workflows/{path.name}')
        _docker_exec('n8n', 'update:workflow', f'--id={_workflow_id(path)}', '--active=true')

    subprocess.check_call(
        ['docker', 'compose', '-f', common.COMPOSE_FILE, 'restart', 'n8n'],
        stderr=subprocess.STDOUT,
    )
    WaitFor(_n8n_healthy, attempts=45, wait=2)()
    if not common.IS_LAB:
        # /healthz returns 200 before webhook routes are re-registered (visible on n8n 2.x);
        # wait for the integration-test webhook to actually serve before downstream conditions.
        WaitFor(_test_webhook_registered, attempts=30, wait=2)()


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
    last_status: int | None = None
    last_exc: Exception | None = None
    for _ in range(iterations):
        try:
            ok = requests.get(f'{base_url}{WEBHOOK_OK_PATH}', timeout=5)
            last_status = ok.status_code
            # 4xx means the webhook responded but didn't execute the workflow (e.g. not yet
            # registered after restart); only 200 proves the workflow body ran end-to-end.
            if ok.status_code == 200:
                ok_responses += 1
        except requests.RequestException as exc:
            last_exc = exc
        # Webhook fail is *expected* to error out — that's the point of triggering it.
        for path in (WEBHOOK_FAIL_PATH, *api_paths):
            with suppress(requests.RequestException):
                requests.get(f'{base_url}{path}', timeout=5)
    if ok_responses == 0:
        raise RuntimeError(
            f'Test webhook returned no 200 responses (last_status={last_status}, last_exc={last_exc!r}); '
            'workflow registration likely failed'
        )


def _workflow_started_non_zero() -> None:
    """WaitFor predicate: succeeds once any ``n8n_workflow_started_total`` sample is non-zero.

    Raises with the last seen samples on failure so that ``WaitFor``'s ``RetryError`` surfaces
    actionable diagnostics on timeout (e.g. n8n renamed the counter, or no execution fired).
    Parses the metric value as a float so that ``0.0`` / ``0e+0`` are recognised as zero and
    ``# HELP``/``# TYPE`` comment lines that happen to share the prefix are skipped.
    """
    payload = requests.get(common.MAIN_INSTANCE['openmetrics_endpoint'], timeout=3).text
    matching: list[str] = []
    for line in payload.splitlines():
        if line.startswith('#') or not line.startswith('n8n_workflow_started_total'):
            continue
        matching.append(line)
        try:
            value = float(line.rsplit(' ', 1)[-1])
        except ValueError:
            continue
        if value > 0:
            return
    raise RuntimeError(f'No non-zero workflow_started_total samples yet. Last seen: {matching or "<none>"}')


@pytest.fixture(scope='session')
def dd_environment() -> Iterator[Any]:
    conditions: list[Any] = [
        # n8n main is booted and serving /metrics.
        CheckEndpoints(common.MAIN_INSTANCE['openmetrics_endpoint']),
        # Import + activate workflows, restart n8n so webhooks register, wait for /healthz.
        _activate_imported_workflows,
        # Worker is checked *after* the main restart so any cascade effect on the worker is caught
        # before downstream conditions try to talk to it. ``docker compose restart n8n`` does not
        # touch the worker today, but the assertion is cheap and forward-proofs against changes.
        CheckEndpoints(common.WORKER_INSTANCE['openmetrics_endpoint']),
    ]
    if not common.IS_LAB:
        # Fire enough webhook traffic to register samples for the workflow and HTTP histograms,
        # then wait until ``n8n_workflow_started_total`` actually goes non-zero. Both stay in
        # ``conditions`` so that ``docker_run``'s ``attempts=2`` retry covers transient failures
        # without leaving these calls exposed to the post-yield teardown path.
        conditions.append(_generate_workflow_traffic)
        conditions.append(WaitFor(_workflow_started_non_zero, attempts=15, wait=2))

    instances = {'instances': [common.MAIN_INSTANCE, common.WORKER_INSTANCE]}
    with docker_run(common.COMPOSE_FILE, conditions=conditions, env_vars=common.get_compose_env_vars()):
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
            yield instances, common.E2E_METADATA


@pytest.fixture
def instance() -> dict[str, Any]:
    return copy.deepcopy(common.MAIN_INSTANCE)


@pytest.fixture
def worker_instance() -> dict[str, Any]:
    return copy.deepcopy(common.WORKER_INSTANCE)
