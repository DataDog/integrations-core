# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os


def running_in_ci():
    for env_var in ('CI', 'GITHUB_ACTIONS'):
        if os.environ.get(env_var) in ('true', '1'):
            return True

    return False


# Functions ported from datadog_checks_dev.ci for old CLI compatibility


def running_on_gh_actions():
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
    return ('AGENT_OS', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')


def _running_on_azp_ci():
    return 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI' in os.environ


def _running_on_azp_windows_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Windows_NT'


def _running_on_azp_linux_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Linux'


def _running_on_azp_macos_ci():
    return _running_on_azp_ci() and os.environ.get('AGENT_OS') == 'Darwin'
