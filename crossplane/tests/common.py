# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()
FIXTURES_DIR = os.path.join(HERE, 'fixtures')

MOCKED_INSTANCE = {'openmetrics_endpoint': 'http://crossplane:8080/metrics'}


def get_fixture_path(endpoint: str) -> str:
    return os.path.join(FIXTURES_DIR, f'{endpoint}_metrics.txt')


# Signals the product brief calls out for each endpoint: reconciliation health, composition
# function runs and circuit breaker activity on core; managed resource state on providers.
CORE_METRICS = [
    'crossplane.controller_runtime.reconcile.count',
    'crossplane.controller_runtime.reconcile.errors.count',
    'crossplane.controller_runtime.reconcile.time_seconds.count',
    'crossplane.workqueue.depth',
    'crossplane.circuit_breaker.events.count',
    'crossplane.engine.controllers.started.count',
    'crossplane.engine.watches.started.count',
    'crossplane.function.run_function.request.count',
    'crossplane.function.run_function.response.count',
    'crossplane.function.run_function.seconds.count',
]

PROVIDER_METRICS = [
    'crossplane.controller_runtime.reconcile.count',
    'crossplane.workqueue.depth',
    'crossplane.managed_resource.exists',
    'crossplane.managed_resource.ready',
    'crossplane.managed_resource.synced',
    'crossplane.managed_resource.first_time_to_readiness_seconds.count',
    'crossplane.managed_resource.first_time_to_reconcile_seconds.count',
]

# Documented upstream but absent from the captured fixtures: they need optional features
# (function response cache), resource deletion or drift, circuit breaker trips, or an
# Upjet-based provider, none of which the test environment exercises.
DOC_ONLY_METRICS = {
    'crossplane.circuit_breaker.opens.count',
    'crossplane.circuit_breaker.closes.count',
    'crossplane.engine.controllers.stopped.count',
    'crossplane.engine.watches.stopped.count',
    'crossplane.function.response_cache.hits.count',
    'crossplane.function.response_cache.misses.count',
    'crossplane.function.response_cache.errors.count',
    'crossplane.function.response_cache.writes.count',
    'crossplane.function.response_cache.deletes.count',
    'crossplane.function.response_cache.bytes.written.count',
    'crossplane.function.response_cache.bytes.deleted.count',
    'crossplane.function.response_cache.read_seconds.bucket',
    'crossplane.function.response_cache.read_seconds.count',
    'crossplane.function.response_cache.read_seconds.sum',
    'crossplane.function.response_cache.write_seconds.bucket',
    'crossplane.function.response_cache.write_seconds.count',
    'crossplane.function.response_cache.write_seconds.sum',
    'crossplane.managed_resource.deletion_seconds.bucket',
    'crossplane.managed_resource.deletion_seconds.count',
    'crossplane.managed_resource.deletion_seconds.sum',
    'crossplane.managed_resource.drift_seconds.bucket',
    'crossplane.managed_resource.drift_seconds.count',
    'crossplane.managed_resource.drift_seconds.sum',
    'crossplane.upjet.resource.ext_api_duration.bucket',
    'crossplane.upjet.resource.ext_api_duration.count',
    'crossplane.upjet.resource.ext_api_duration.sum',
    'crossplane.upjet.resource.external_api_calls.count',
    'crossplane.upjet.resource.deletion_seconds.bucket',
    'crossplane.upjet.resource.deletion_seconds.count',
    'crossplane.upjet.resource.deletion_seconds.sum',
    'crossplane.upjet.resource.reconcile_delay_seconds.bucket',
    'crossplane.upjet.resource.reconcile_delay_seconds.count',
    'crossplane.upjet.resource.reconcile_delay_seconds.sum',
    'crossplane.upjet.resource.ttr.bucket',
    'crossplane.upjet.resource.ttr.count',
    'crossplane.upjet.resource.ttr.sum',
    'crossplane.upjet.terraform.cli_duration.bucket',
    'crossplane.upjet.terraform.cli_duration.count',
    'crossplane.upjet.terraform.cli_duration.sum',
    'crossplane.upjet.terraform.active_cli_invocations',
    'crossplane.upjet.terraform.running_processes',
}
