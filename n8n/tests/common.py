# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import find_free_ports, get_metadata_metrics

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()

# Allocate free host ports once per session. The values are forwarded to docker compose via
# the ``env_vars`` argument of ``docker_run`` (see ``conftest.py``) so re-runs don't collide
# with stale containers or other locally-bound services. The in-container ports stay fixed.
MAIN_PORT, WORKER_PORT = find_free_ports('127.0.0.1', 2)

N8N_VERSION = os.environ.get('N8N_VERSION', '1.118.1')
N8N_MAJOR = int(N8N_VERSION.split('.', 1)[0])

# Submitted by the check itself, not by the OpenMetrics scrape.
CHECK_LEVEL_METRIC_NAMES = frozenset({'n8n.readiness.check'})

# Metric families introduced in n8n 2.x — verified live against n8n@1.118.1 and n8n@2.19.5.
V2_ONLY_METRIC_NAMES = frozenset(
    {
        'n8n.audit.workflow.activated.count',
        'n8n.audit.workflow.deactivated.count',
        'n8n.audit.workflow.executed.count',
        'n8n.audit.workflow.resumed.count',
        'n8n.audit.workflow.version.updated.count',
        'n8n.audit.workflow.waiting.count',
        'n8n.credentials.total',
        'n8n.embed.login.failures.count',
        'n8n.embed.login.requests.count',
        'n8n.enabled.users',
        'n8n.expression.code.cache.eviction.count',
        'n8n.expression.code.cache.hit.count',
        'n8n.expression.code.cache.miss.count',
        'n8n.expression.code.cache.size',
        'n8n.expression.evaluation.duration.seconds.bucket',
        'n8n.expression.evaluation.duration.seconds.count',
        'n8n.expression.evaluation.duration.seconds.sum',
        'n8n.expression.pool.acquired.count',
        'n8n.expression.pool.replenish.failed.count',
        'n8n.expression.pool.scaled.to.zero.count',
        'n8n.expression.pool.scaled.up.count',
        'n8n.manual.executions',
        'n8n.process.pss.bytes',
        'n8n.production.executions',
        'n8n.production.root.executions',
        'n8n.token.exchange.failures.count',
        'n8n.token.exchange.identity.linked.count',
        'n8n.token.exchange.jit.provisioning.count',
        'n8n.token.exchange.requests.count',
        'n8n.users.total',
        'n8n.workflow.execution.duration.seconds.bucket',
        'n8n.workflow.execution.duration.seconds.count',
        'n8n.workflow.execution.duration.seconds.sum',
        'n8n.workflows.total',
    }
)

# Metrics that are mapped and present in metadata but only emit samples after a specific
# event fires (auth failure, audit state transition, libuv request mid-flight). The unit
# fixture has synthetic samples for them; live integration/e2e runs cannot guarantee
# samples and exclude them from the symmetric metadata assertion.
RARE_EVENT_METRIC_NAMES = frozenset(
    {
        'n8n.audit.workflow.archived.count',
        'n8n.audit.workflow.created.count',
        'n8n.audit.workflow.deactivated.count',
        'n8n.audit.workflow.deleted.count',
        'n8n.audit.workflow.resumed.count',
        'n8n.audit.workflow.unarchived.count',
        'n8n.audit.workflow.updated.count',
        'n8n.audit.workflow.version.updated.count',
        'n8n.audit.workflow.waiting.count',
        'n8n.embed.login.failures.count',
        # Expression-engine observability metrics: gated on N8N_EXPRESSION_ENGINE=vm and
        # N8N_EXPRESSION_ENGINE_OBSERVABILITY_ENABLED=true, neither of which the test or
        # lab compose enable. Mapped + documented; live containers don't emit them.
        'n8n.expression.code.cache.eviction.count',
        'n8n.expression.code.cache.hit.count',
        'n8n.expression.code.cache.miss.count',
        'n8n.expression.code.cache.size',
        'n8n.expression.evaluation.duration.seconds.bucket',
        'n8n.expression.evaluation.duration.seconds.count',
        'n8n.expression.evaluation.duration.seconds.sum',
        'n8n.expression.pool.acquired.count',
        'n8n.expression.pool.replenish.failed.count',
        'n8n.expression.pool.scaled.to.zero.count',
        'n8n.expression.pool.scaled.up.count',
        'n8n.queue.job.stalled.count',
        'n8n.runner.task.requested.count',
        'n8n.token.exchange.failures.count',
        # prom-client's per-type libuv request gauge: only has samples while a libuv request is in flight
        # at scrape time, so live containers can produce or omit it depending on timing.
        'n8n.nodejs.active.requests',
    }
)

MAIN_INSTANCE = {
    'openmetrics_endpoint': f'http://{HOST}:{MAIN_PORT}/metrics',
    'tags': ['n8n_process:main'],
}
WORKER_INSTANCE = {
    'openmetrics_endpoint': f'http://{HOST}:{WORKER_PORT}/metrics',
    'tags': ['n8n_process:worker'],
}
INSTANCE = MAIN_INSTANCE  # back-compat default for unit tests

E2E_METADATA = {'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro']}


def get_compose_env_vars() -> dict[str, str]:
    """Variables consumed by docker-compose.yaml's ``${...}`` placeholders."""
    return {
        'N8N_MAIN_HOST_PORT': str(MAIN_PORT),
        'N8N_WORKER_HOST_PORT': str(WORKER_PORT),
    }


def get_fixture_path(filename: str) -> str:
    return os.path.join(HERE, 'fixtures', filename)


def get_metadata_metrics_for_version(major: int = N8N_MAJOR, *, exclude_rare: bool = False) -> dict:
    """Return the metadata.csv subset that the given n8n major version is expected to emit."""
    metadata = get_metadata_metrics()
    if major < 2:
        for name in V2_ONLY_METRIC_NAMES:
            metadata.pop(name, None)
    if exclude_rare:
        for name in RARE_EVENT_METRIC_NAMES:
            metadata.pop(name, None)
    return metadata


def get_openmetrics_metadata_metrics(major: int = N8N_MAJOR, *, exclude_rare: bool = False) -> dict:
    """Version-aware metadata subset minus metrics submitted by the check itself."""
    metadata = get_metadata_metrics_for_version(major, exclude_rare=exclude_rare)
    for name in CHECK_LEVEL_METRIC_NAMES:
        metadata.pop(name, None)
    return metadata


def get_all_metadata_metrics(major: int = N8N_MAJOR, *, exclude_rare: bool = False) -> dict:
    """Version-aware metadata subset including the readiness gauge submitted by the check."""
    return get_metadata_metrics_for_version(major, exclude_rare=exclude_rare)


def drop_rare_event_metrics(aggregator: AggregatorStub):
    """Strip rare-event metrics from the aggregator before a symmetric metadata assertion.

    These metrics are mapped and present in metadata.csv but only emit samples opportunistically
    (auth failures, libuv requests in flight). Live containers may submit them or not depending on
    timing, which makes ``check_symmetric_inclusion=True`` flaky in either direction. Dropping them
    from the aggregator (and from the metadata subset via ``exclude_rare=True``) keeps the
    symmetric check stable while still verifying the rest of the surface end-to-end.
    """
    for name in RARE_EVENT_METRIC_NAMES:
        aggregator._metrics.pop(name, None)
