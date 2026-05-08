# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

METRIC_NAMESPACE_METRICS = 'datadog.agent.metrics'
METRIC_NAMESPACE_PROFILE = 'datadog.agent.profile'


def get_agent_embedded_path(*parts: str) -> str | None:
    """Resolve a path under the agent's `embedded` directory from the agent's `run_path` config.

    Returns ``None`` when ``run_path`` is unset so callers can decide whether the
    miss is fatal or merely skips a fallback. Works for both the standard install
    (``/opt/datadog-agent/run``) and Remote-Management installs
    (``/opt/datadog-packages/datadog-agent/<version>/run``).
    """
    run_path = datadog_agent.get_config('run_path')
    if not run_path:
        return None
    install_path = run_path[:-4] if run_path.endswith('/run') else run_path
    return os.path.join(install_path, 'embedded', *parts)
