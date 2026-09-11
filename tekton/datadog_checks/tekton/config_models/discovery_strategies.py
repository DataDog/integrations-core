# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can define custom (local:) discovery strategies for this integration.
#
# Decorate a generator with @discovery_strategy (imported from
# datadog_checks.base.utils.discovery) and reference it from the spec discovery
# stanza as `strategy: local:<function_name>`. The function receives the
# discovered Service plus the inputs declared in the spec and yields one context
# (ctx) mapping per candidate, exposing the keys listed in `provides`.
#
# from datadog_checks.base.utils.discovery import discovery_strategy
#
# @discovery_strategy(provides=('svc',))
# def from_some_config(service, config_path):
#     ...
#     yield {'svc': ...}

from datadog_checks.base.utils.discovery import Port, discovery_strategy


@discovery_strategy(provides=('port',))
def from_default_metrics_port(service, port):
    """Yield a hardcoded default metrics port when the service has no named ``metrics`` port.

    The Tekton Triggers Controller serves Prometheus metrics on its default port
    (9000) without declaring it as a ``containerPort`` in its pod spec, so
    Kubelet-based Autodiscovery never sees the port. Fall back to the default
    port only when the named-port strategy has nothing to work with; this keeps
    the fallback silent for services that do declare their metrics port (such as
    the Pipelines Controller, which declares a ``metrics`` containerPort).
    """
    if any(service_port.name == 'metrics' for service_port in service.ports):
        return
    yield {'port': Port(number=port)}
