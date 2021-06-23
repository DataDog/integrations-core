# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os.path import expanduser

from .platform import LINUX, MAC, WINDOWS

DEFAULT_AGENT_VERSION = 7
DEFAULT_PYTHON_VERSION = 3

# Make checks run at most once every second
DEFAULT_SAMPLING_COLLECTION_INTERVAL = 1

# Number of seconds to ensure the Agent is running for prior to shutting down
#
# We want each run to collect at least 10 samples. The time consuming parts like
# spinning up Docker environments are done during the setup phase, so the test phase
# is merely a tox invocation that runs E2E tests via `pytest`.
DEFAULT_SAMPLING_WAIT_TIME = 15

# Must be a certain length
FAKE_API_KEY = 'a' * 32

MANIFEST_VERSION_PATTERN = r'agent (\d)'

DEFAULT_DOGSTATSD_PORT = 8125


def get_rate_flag(agent_version):
    if agent_version >= 6:
        return '--check-rate'
    else:
        return 'check_rate'


def get_agent_exe(agent_version, platform=LINUX):
    if platform == WINDOWS:
        if agent_version >= 6:
            return r'C:\Program Files\Datadog\Datadog Agent\bin\agent.exe'
        else:
            # [TODO] Actually get the path here
            pass
    elif platform == MAC:
        if agent_version >= 6:
            return 'datadog-agent'
        else:
            return 'dd-agent'
    else:
        if agent_version >= 6:
            return '/opt/datadog-agent/bin/agent/agent'
        else:
            return '/opt/datadog-agent/agent/agent.py'


def get_python_exe(platform=LINUX, python_version=DEFAULT_PYTHON_VERSION):
    if platform == WINDOWS:
        return r'C:\Program Files\Datadog\Datadog Agent\embedded{}\python.exe'.format(python_version)
    else:
        return f'/opt/datadog-agent/embedded/bin/python{python_version}'


def get_pip_exe(python_version, platform=LINUX):
    if platform == WINDOWS:
        return [get_python_exe(platform=platform, python_version=python_version), '-m', 'pip']
    else:
        return [f'/opt/datadog-agent/embedded/bin/pip{python_version}']


def get_agent_conf_dir(check, agent_version, platform=LINUX):
    if platform == WINDOWS:
        if agent_version >= 6:
            return r'C:\ProgramData\Datadog\conf.d\{}.d'.format(check)
        else:
            return r'C:\ProgramData\Datadog\conf.d'
    elif platform == MAC:
        if agent_version >= 6:
            return f'/opt/datadog-agent/etc/conf.d/{check}.d'
        else:
            return '/opt/datadog-agent/etc/conf.d'
    else:
        if agent_version >= 6:
            return f'/etc/datadog-agent/conf.d/{check}.d'
        else:
            return '/etc/dd-agent/conf.d'


def get_agent_version_manifest(platform):
    if platform == WINDOWS:
        return r'C:\Program Files\Datadog\Datadog Agent\version-manifest.txt'
    else:
        return '/opt/datadog-agent/version-manifest.txt'


def get_agent_service_cmd(version, platform, action):
    if platform == WINDOWS:
        arg = 'start-service' if action == 'start' else 'stopservice'
        return (
            r'powershell -executionpolicy bypass -Command Start-Process """""""""C:\Program Files\Datadog\Datadog '
            r'Agent\embedded\agent.exe""""""""" -Verb runAs -argumentlist {}'.format(arg)
        )
    elif platform == MAC:
        return [
            'launchctl',
            'load' if action == 'start' else 'unload',
            '-w',
            f"{expanduser('~')}/Library/LaunchAgents/com.datadoghq.agent.plist",
        ]
    else:
        return ['sudo', 'service', 'datadog-agent', action]
