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
