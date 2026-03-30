# ABOUTME: Datadog Agent check for Apache NiFi.
# ABOUTME: Polls the NiFi REST API to collect JVM, flow, queue, processor, and bulletin data.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck


class NifiCheck(AgentCheck):
    __NAMESPACE__ = 'nifi'

    def check(self, _):
        pass
