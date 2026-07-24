# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable, Iterator
from typing import Any

from datadog_checks.base.utils.discovery import Service

# Override the generated discovery candidates() for this integration.
#
# Define a candidates(service, default) function to wrap or replace the generated
# candidate generation. `default` is the generated generator; call it to reuse
# the spec-driven candidates, or ignore it to replace them entirely.
#
# def candidates(service, default):
#     yield from default(service)


def candidates(service: Service, default: Callable[[Service], Iterator[dict[str, Any]]]) -> Iterator[dict[str, Any]]:
    for candidate in default(service):
        init_config = candidate.get('init_config', {})
        # The generated config models serialize defaults, but `fluentd` is a secure command
        # field. During discovery probes there is no trusted config provider, so emitting the
        # implicit default makes the candidate look like it configured an untrusted secure
        # value. The check falls back to `fluentd` when this option is absent.
        if init_config.get('fluentd') == 'fluentd':
            init_config.pop('fluentd')

        for instance in candidate.get('instances', []):
            if instance.get('fluentd') == 'fluentd':
                instance.pop('fluentd')

        yield candidate
