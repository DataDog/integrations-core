# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
CI utilities
"""
import os


def get_ci_env_vars():
    return ('AGENT_OS', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')


def running_on_ci():
    if 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI' in os.environ or 'Pipeline.Workspace' in os.environ:
        return True
    for env_var in ('CI', 'GITHUB_ACTIONS'):
        if os.environ.get(env_var) in ('true', '1'):
            return True
    return False


def running_on_windows_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Windows_NT'


def running_on_linux_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Linux'


def running_on_macos_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Darwin'


def running_on_gh_actions():
    # GITHUB_ACTIONS always set to true when GitHub Actions is running the workflow.
    return os.environ.get('GITHUB_ACTIONS') == 'true'
