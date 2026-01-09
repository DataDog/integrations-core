# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 5678


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


OPENMETRICS_URL = f'http://{HOST}:{PORT}'
INSTANCE = {
    'openmetrics_endpoint': f'{OPENMETRICS_URL}/metrics',
    'raw_metric_prefix': 'n8n_',
}

E2E_METADATA = {
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
}

TEST_METRICS = [
    'n8n.active.workflow.count',
    'n8n.api.request.duration.seconds.bucket',
    'n8n.api.request.duration.seconds.count',
    'n8n.api.request.duration.seconds.sum',
    'n8n.api.requests.count',
    'n8n.cache.errors.count',
    'n8n.cache.hits.count',
    'n8n.cache.latency.seconds.bucket',
    'n8n.cache.latency.seconds.count',
    'n8n.cache.latency.seconds.sum',
    'n8n.cache.misses.count',
    'n8n.cache.operations.count',
    'n8n.eventbus.connections.total',
    'n8n.eventbus.events.failed.count',
    'n8n.eventbus.events.processed.count',
    'n8n.eventbus.events.count',
    'n8n.eventbus.queue.size',
    'n8n.instance.role.leader',
    'n8n.last.activity',
    'n8n.nodejs.active.handles',
    'n8n.nodejs.active.handles.total',
    'n8n.nodejs.active.requests.total',
    'n8n.nodejs.active.resources',
    'n8n.nodejs.active.resources.total',
    'n8n.nodejs.event.loop.lag.seconds',
    'n8n.nodejs.eventloop.lag.max.seconds',
    'n8n.nodejs.eventloop.lag.mean.seconds',
    'n8n.nodejs.eventloop.lag.min.seconds',
    'n8n.nodejs.eventloop.lag.p50.seconds',
    'n8n.nodejs.eventloop.lag.p90.seconds',
    'n8n.nodejs.eventloop.lag.p99.seconds',
    'n8n.nodejs.eventloop.lag.seconds',
    'n8n.nodejs.eventloop.lag.stddev.seconds',
    'n8n.nodejs.external.memory.bytes',
    'n8n.nodejs.gc.duration.seconds.bucket',
    'n8n.nodejs.gc.duration.seconds.count',
    'n8n.nodejs.gc.duration.seconds.sum',
    'n8n.nodejs.heap.size.total.bytes',
    'n8n.nodejs.heap.size.used.bytes',
    'n8n.nodejs.heap.space.size.available.bytes',
    'n8n.nodejs.heap.space.size.total.bytes',
    'n8n.nodejs.heap.space.size.used.bytes',
    'n8n.nodejs.heap.total.bytes',
    'n8n.nodejs.heap.used.bytes',
    'n8n.process.cpu.system.seconds.count',
    'n8n.process.cpu.user.seconds.count',
    'n8n.process.heap.bytes',
    'n8n.process.max.fds',
    'n8n.process.open.fds',
    'n8n.process.resident.memory.bytes',
    'n8n.process.uptime.seconds',
    'n8n.process.virtual.memory.bytes',
    'n8n.queue.job.active.total',
    'n8n.queue.job.attempts.count',
    'n8n.queue.job.completed.count',
    'n8n.queue.job.delayed.total',
    'n8n.queue.job.dequeued.count',
    'n8n.queue.job.enqueued.count',
    'n8n.queue.job.failed.count',
    'n8n.queue.job.waiting.duration.seconds.bucket',
    'n8n.queue.job.waiting.duration.seconds.count',
    'n8n.queue.job.waiting.duration.seconds.sum',
    'n8n.queue.job.waiting.total',
    'n8n.queue.jobs.duration.seconds.bucket',
    'n8n.queue.jobs.duration.seconds.count',
    'n8n.queue.jobs.duration.seconds.sum',
    'n8n.queue.jobs.count',
    'n8n.readiness.check',
    'n8n.workflow.executions.active',
    'n8n.workflow.executions.duration.seconds.bucket',
    'n8n.workflow.executions.duration.seconds.count',
    'n8n.workflow.executions.duration.seconds.sum',
    'n8n.workflow.executions.count',
    'n8n.workflow.failed.count',
    'n8n.workflow.started.count',
    'n8n.workflow.success.count',
    'n8n.process.cpu.seconds.count',
]
