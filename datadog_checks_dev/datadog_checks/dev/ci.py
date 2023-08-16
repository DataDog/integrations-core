# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
CI utilities
"""
import os


def running_on_gh_actions():
    # GITHUB_ACTIONS always set to true when GitHub Actions is running the workflow.
    # https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables
    return os.environ.get('GITHUB_ACTIONS') == 'true'


def running_on_ci():
    return running_on_gh_actions() or _running_on_azp_ci()


def running_on_windows_ci():
    return (running_on_gh_actions() and os.environ.get('RUNNER_OS') == 'Windows') or _running_on_azp_windows_ci()


def running_on_linux_ci():
    return (running_on_gh_actions() and os.environ.get('RUNNER_OS') == 'Linux') or _running_on_azp_linux_ci()


def running_on_macos_ci():
    return (running_on_gh_actions() and os.environ.get('RUNNER_OS') == 'macOS') or _running_on_azp_macos_ci()


def get_ci_env_vars():
    # TODO: Remove this as it is unused
    return ('AGENT_OS', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')


def _running_on_azp_ci():
    return 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI' in os.environ


def _running_on_azp_windows_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Windows_NT'


def _running_on_azp_linux_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Linux'


def _running_on_azp_macos_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Darwin'
