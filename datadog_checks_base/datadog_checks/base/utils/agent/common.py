# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

METRIC_NAMESPACE_METRICS = 'datadog.agent.metrics'
METRIC_NAMESPACE_PROFILE = 'datadog.agent.profile'


def get_agent_embedded_path(*parts: str) -> str | None:
    """Resolve a path under the agent's `embedded` directory.

    On Linux, derives the install directory from the agent's ``run_path`` config,
    which handles both the standard install (``/opt/datadog-agent/run``) and
    Remote-Management installs (``/opt/datadog-packages/datadog-agent/<version>/run``).
    Returns ``None`` when ``run_path`` is unset.

    On Windows, ``run_path`` is a writable cache directory under ``%ProgramData%``
    that is unrelated to the install directory, so the install directory is derived
    from ``sys.executable`` (the agent's embedded Python) instead, and the embedded
    directory is named ``embedded3``.
    """
    if os.name == 'nt':
        install_path = sys.executable.split('embedded')[0].rstrip(os.sep)
        return os.path.join(install_path, 'embedded3', *parts)
    run_path = datadog_agent.get_config('run_path')
    if not run_path:
        return None
    install_path = run_path[:-4] if run_path.endswith('/run') else run_path
    return os.path.join(install_path, 'embedded', *parts)
