# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_METRICS = [
    # General Metrics
    'traefik_mesh.go.info',
    'traefik_mesh.go.gc.duration.seconds.count',
    'traefik_mesh.go.gc.duration.seconds.quantile',
    'traefik_mesh.go.gc.duration.seconds.sum',
    'traefik_mesh.go.goroutines',
    'traefik_mesh.go.memstats.alloc_bytes',
    'traefik_mesh.go.memstats.alloc_bytes.count',
    'traefik_mesh.go.memstats.buck_hash.sys_bytes',
    'traefik_mesh.go.memstats.frees.count',
    'traefik_mesh.go.memstats.gc.cpu_fraction',
    'traefik_mesh.go.memstats.gc.sys_bytes',
    'traefik_mesh.go.memstats.heap.alloc_bytes',
    'traefik_mesh.go.memstats.heap.idle_bytes',
    'traefik_mesh.go.memstats.heap.inuse_bytes',
    'traefik_mesh.go.memstats.heap.objects',
    'traefik_mesh.go.memstats.heap.released_bytes',
    'traefik_mesh.go.memstats.heap.sys_bytes',
    'traefik_mesh.go.memstats.last_gc_time.seconds',
    'traefik_mesh.go.memstats.lookups.count',
    'traefik_mesh.go.memstats.mallocs.count',
    'traefik_mesh.go.memstats.mcache.inuse_bytes',
    'traefik_mesh.go.memstats.mcache.sys_bytes',
    'traefik_mesh.go.memstats.mspan.inuse_bytes',
    'traefik_mesh.go.memstats.mspan.sys_bytes',
    'traefik_mesh.go.memstats.next.gc_bytes',
    'traefik_mesh.go.memstats.other.sys_bytes',
    'traefik_mesh.go.memstats.stack.inuse_bytes',
    'traefik_mesh.go.memstats.stack.sys_bytes',
    'traefik_mesh.go.memstats.sys_bytes',
    'traefik_mesh.go.threads',
    'traefik_mesh.process.cpu.seconds.count',
    'traefik_mesh.process.max_fds',
    'traefik_mesh.process.open_fds',
    'traefik_mesh.process.resident_memory.bytes',
    'traefik_mesh.process.start_time.seconds',
    'traefik_mesh.process.virtual_memory.bytes',
    'traefik_mesh.process.virtual_memory.max_bytes',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#global-metrics
    'traefik_mesh.config.last_reload.failure',
    'traefik_mesh.config.last_reload.success',
    'traefik_mesh.config.reloads.count',
    'traefik_mesh.config.reloads.failure.count',
    'traefik_mesh.tls.certs.not_after',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#entrypoint-metrics
    'traefik_mesh.entrypoint.open_connections',
    'traefik_mesh.entrypoint.request.duration.seconds.bucket',
    'traefik_mesh.entrypoint.request.duration.seconds.count',
    'traefik_mesh.entrypoint.request.duration.seconds.sum',
    'traefik_mesh.entrypoint.requests.count',
    'traefik_mesh.entrypoint.requests.bytes.count',
    'traefik_mesh.entrypoint.requests.tls.count',
    'traefik_mesh.entrypoint.responses.bytes.count',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#router-metrics
    'traefik_mesh.router.open_connections',
    'traefik_mesh.router.request.duration.seconds.bucket',
    'traefik_mesh.router.request.duration.seconds.count',
    'traefik_mesh.router.request.duration.seconds.sum',
    'traefik_mesh.router.requests.bytes.count',
    'traefik_mesh.router.requests.count',
    'traefik_mesh.router.requests.tls.count',
    'traefik_mesh.router.responses.bytes.count',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#service-metrics
    'traefik_mesh.service.open_connections',
    'traefik_mesh.service.request.duration.seconds.bucket',
    'traefik_mesh.service.request.duration.seconds.count',
    'traefik_mesh.service.request.duration.seconds.sum',
    'traefik_mesh.service.requests.count',
    'traefik_mesh.service.tls.requests.count',
    'traefik_mesh.service.requests.bytes.count',
    'traefik_mesh.service.responses.bytes.count',
    'traefik_mesh.service.retries.count',
    'traefik_mesh.service.server.up',
]

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:traefik_mesh'],
}

OM_MOCKED_INSTANCE_CONTROLLER = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'traefik_controller_api_endpoint': 'http://localhost:8081',
    'tags': ['test:traefik_mesh'],
}

OPTIONAL_METRICS = {
    'traefik_mesh.tls.certs.not_after',
    'traefik_mesh.entrypoint.requests.bytes.count',
    'traefik_mesh.entrypoint.requests.tls.count',
    'traefik_mesh.entrypoint.responses.bytes.count',
    'traefik_mesh.router.open_connections',
    'traefik_mesh.router.request.duration.seconds.bucket',
    'traefik_mesh.router.request.duration.seconds.count',
    'traefik_mesh.router.request.duration.seconds.sum',
    'traefik_mesh.router.requests.bytes.count',
    'traefik_mesh.router.requests.count',
    'traefik_mesh.router.requests.tls.count',
    'traefik_mesh.router.responses.bytes.count',
    'traefik_mesh.service.tls.requests.count',
    'traefik_mesh.service.requests.bytes.count',
    'traefik_mesh.service.responses.bytes.count',
    'traefik_mesh.service.retries.count',
    'traefik_mesh.service.server.up',
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def read_json_fixture(filename):
    with open(get_fixture_path(filename), 'r') as f:
        return json.load(f)
