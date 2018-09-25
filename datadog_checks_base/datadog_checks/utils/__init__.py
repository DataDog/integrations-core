# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent
    if datadog_agent.get_config('integration_tracing'):
        from ddtrace import patch
        patch(requests=True)
except ImportError:
    # Tracing Integrations is only available with Agent 6
    pass
