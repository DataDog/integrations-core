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
}
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


E2E_METADATA = {
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
}

E2E_METRICS = [
    'n8n.active.workflow.count',
    'n8n.api.request.duration.seconds.count',
    'n8n.api.request.duration.seconds.sum',
    'n8n.api.requests.total',
    'n8n.cache.errors.total',
    'n8n.cache.hits.total',
    'n8n.cache.latency.seconds.count',
    'n8n.cache.latency.seconds.sum',
    'n8n.cache.misses.total',
    'n8n.cache.operations.total',
    'n8n.eventbus.connections.total',
    'n8n.eventbus.events.failed.total',
    'n8n.eventbus.events.processed.total',
    'n8n.eventbus.events.total',
    'n8n.eventbus.queue.size',
    'n8n.http.request.duration.seconds.count',
    'n8n.http.request.duration.seconds.sum',
    'n8n.instance.role.leader',
    'n8n.last.activity',
    'n8n.nodejs.active.handles',
    'n8n.nodejs.active.handles.total',
    'n8n.nodejs.active.requests',
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
    'n8n.nodejs.gc.duration.seconds.count',
    'n8n.nodejs.gc.duration.seconds.sum',
    'n8n.nodejs.heap.size.total.bytes',
    'n8n.nodejs.heap.size.used.bytes',
    'n8n.nodejs.heap.space.size.available.bytes',
    'n8n.nodejs.heap.space.size.total.bytes',
    'n8n.nodejs.heap.space.size.used.bytes',
    'n8n.nodejs.heap.total.bytes',
    'n8n.nodejs.heap.used.bytes',
    'n8n.nodejs.version.info',
    'n8n.process.cpu.system.seconds.total',
    'n8n.process.cpu.user.seconds.total',
    'n8n.process.heap.bytes',
    'n8n.process.max.fds',
    'n8n.process.open.fds',
    'n8n.process.resident.memory.bytes',
    'n8n.process.start.time.seconds',
    'n8n.process.virtual.memory.bytes',
    'n8n.queue.job.attempts.total',
    'n8n.queue.jobs.duration.seconds.count',
    'n8n.queue.jobs.duration.seconds.sum',
    'n8n.queue.jobs.total',
    'n8n.workflow.executions.active',
    'n8n.workflow.executions.duration.seconds.count',
    'n8n.workflow.executions.duration.seconds.sum',
    'n8n.workflow.executions.total',
    'n8n.process.cpu.seconds.total',
    'n8n.version.info',
]
