# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_METRICS = [
    # General Metrics
    'traefik_meshh.go.info',
    'traefik_meshh.go.gc.duration.seconds.count',
    'traefik_meshh.go.gc.duration.seconds.quantile',
    'traefik_meshh.go.gc.duration.seconds.sum',
    'traefik_meshh.go.goroutines',
    'traefik_meshh.go.memstats.alloc_bytes',
    'traefik_meshh.go.memstats.alloc_bytes.count',
    'traefik_meshh.go.memstats.buck_hash.sys_bytes',
    'traefik_meshh.go.memstats.frees.count',
    'traefik_meshh.go.memstats.gc.cpu_fraction',
    'traefik_meshh.go.memstats.gc.sys_bytes',
    'traefik_meshh.go.memstats.heap.alloc_bytes',
    'traefik_meshh.go.memstats.heap.idle_bytes',
    'traefik_meshh.go.memstats.heap.inuse_bytes',
    'traefik_meshh.go.memstats.heap.objects',
    'traefik_meshh.go.memstats.heap.released_bytes',
    'traefik_meshh.go.memstats.heap.sys_bytes',
    'traefik_meshh.go.memstats.last_gc_time.seconds',
    'traefik_meshh.go.memstats.lookups.count',
    'traefik_meshh.go.memstats.mallocs.count',
    'traefik_meshh.go.memstats.mcache.inuse_bytes',
    'traefik_meshh.go.memstats.mcache.sys_bytes',
    'traefik_meshh.go.memstats.mspan.inuse_bytes',
    'traefik_meshh.go.memstats.mspan.sys_bytes',
    'traefik_meshh.go.memstats.next.gc_bytes',
    'traefik_meshh.go.memstats.other.sys_bytes',
    'traefik_meshh.go.memstats.stack.inuse_bytes',
    'traefik_meshh.go.memstats.stack.sys_bytes',
    'traefik_meshh.go.memstats.sys_bytes',
    'traefik_meshh.go.threads',
    'traefik_meshh.process.cpu.seconds.count',
    'traefik_meshh.process.max_fds',
    'traefik_meshh.process.open_fds',
    'traefik_meshh.process.resident_memory.bytes',
    'traefik_meshh.process.start_time.seconds',
    'traefik_meshh.process.virtual_memory.bytes',
    'traefik_meshh.process.virtual_memory.max_bytes',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#global-metrics
    'traefik_meshh.config.last_reload.failure',
    'traefik_meshh.config.last_reload.success',
    'traefik_meshh.config.reloads.count',
    'traefik_meshh.config.reloads.failure.count',
    'traefik_meshh.tls.certs.not_after',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#entrypoint-metrics
    'traefik_meshh.entrypoint.open_connections',
    'traefik_meshh.entrypoint.request.duration.seconds.bucket',
    'traefik_meshh.entrypoint.request.duration.seconds.count',
    'traefik_meshh.entrypoint.request.duration.seconds.sum',
    'traefik_meshh.entrypoint.requests.count',
    'traefik_meshh.entrypoint.requests.bytes.count',
    'traefik_meshh.entrypoint.requests.tls.count',
    'traefik_meshh.entrypoint.responses.bytes.count',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#router-metrics
    'traefik_meshh.router.open_connections',
    'traefik_meshh.router.request.duration.seconds.bucket',
    'traefik_meshh.router.request.duration.seconds.count',
    'traefik_meshh.router.request.duration.seconds.sum',
    'traefik_meshh.router.requests.bytes.count',
    'traefik_meshh.router.requests.count',
    'traefik_meshh.router.requests.tls.count',
    'traefik_meshh.router.responses.bytes.count',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#service-metrics
    'traefik_meshh.service.open_connections',
    'traefik_meshh.service.request.duration.seconds.bucket',
    'traefik_meshh.service.request.duration.seconds.count',
    'traefik_meshh.service.request.duration.seconds.sum',
    'traefik_meshh.service.requests.count',
    'traefik_meshh.service.tls.requests.count',
    'traefik_meshh.service.requests.bytes.count',
    'traefik_meshh.service.responses.bytes.count',
    'traefik_meshh.service.retries.count',
    'traefik_meshh.service.server.up',
]

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:traefik_meshh'],
}

OM_MOCKED_INSTANCE_CONTROLLER = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'traefik_controller_api_endpoint': 'http://localhost:8081',
    'tags': ['test:traefik_meshh'],
}

OPTIONAL_METRICS = {
    'traefik_meshh.tls.certs.not_after',
    'traefik_meshh.entrypoint.requests.bytes.count',
    'traefik_meshh.entrypoint.requests.tls.count',
    'traefik_meshh.entrypoint.responses.bytes.count',
    'traefik_meshh.router.open_connections',
    'traefik_meshh.router.request.duration.seconds.bucket',
    'traefik_meshh.router.request.duration.seconds.count',
    'traefik_meshh.router.request.duration.seconds.sum',
    'traefik_meshh.router.requests.bytes.count',
    'traefik_meshh.router.requests.count',
    'traefik_meshh.router.requests.tls.count',
    'traefik_meshh.router.responses.bytes.count',
    'traefik_meshh.service.tls.requests.count',
    'traefik_meshh.service.requests.bytes.count',
    'traefik_meshh.service.responses.bytes.count',
    'traefik_meshh.service.retries.count',
    'traefik_meshh.service.server.up',
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def read_json_fixture(filename):
    with open(get_fixture_path(filename), 'r') as f:
        return json.load(f)
