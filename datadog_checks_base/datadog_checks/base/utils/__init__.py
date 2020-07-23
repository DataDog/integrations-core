# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    import datadog_agent

    if datadog_agent.get_config('integration_tracing'):
        from ddtrace import patch

        # handle thread monitoring as an additional option
        # See: http://pypi.datadoghq.com/trace/docs/other_integrations.html#futures
        if datadog_agent.get_config('integration_tracing_futures'):
            patch(requests=True, futures=True)
        else:
            patch(requests=True)

except ImportError:
    # Tracing Integrations is only available with Agent 6
    pass
