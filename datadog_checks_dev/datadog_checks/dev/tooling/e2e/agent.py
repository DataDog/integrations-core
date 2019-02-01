# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform as Platform

from .platform import LINUX, MAC, WINDOWS
from ...utils import HOME

DEFAULT_AGENT_VERSION = 6

# Must be a certain length
FAKE_API_KEY = 'a' * 32

AGENT_CMD = {
    WINDOWS: {
        'start': 'start-service',
        'stop': 'stopservice',
        'pip': [r'C:\Program Files\Datadog\Datadog Agent\embedded\python', '-m', 'pip']
    },
    MAC: {
        'start': 'load',
        'stop': 'unload',
        'pip': ['/opt/datadog-agent/embedded/bin/pip', '--user']
    }
}

MANIFEST_VERSION_PATTERN = r'agent (\d)'


def get_rate_flag(agent_version):
    if agent_version >= 6:
        return '--check-rate'
    else:
        return 'check_rate'


def get_agent_exe(agent_version, platform=LINUX):
    if platform == WINDOWS:
        if agent_version >= 6:
            return r"C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe"
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


def get_agent_conf_dir(check, agent_version, platform=LINUX):
    if platform == WINDOWS:
        if agent_version >= 6:
            return r'C:\ProgramData\Datadog\conf.d\{}.d'.format(check)
        else:
            return r'C:\ProgramData\Datadog\conf.d'
    elif platform == MAC:
        if agent_version >= 6:
            return '{}/.datadog-agent/conf.d/{}.d'.format(HOME, check)
        else:
            return '{}/.datadog-agent/conf.d'.format(HOME)
    else:
        if agent_version >= 6:
            return '/etc/datadog-agent/conf.d/{}.d'.format(check)
        else:
            return '/etc/dd-agent/conf.d'


def get_agent_version_manifest(platform):
    if platform == WINDOWS:
        return r'C:\Program Files\Datadog\Datadog Agent\version-manifest.txt'
    else:
        return '/opt/datadog-agent/version-manifest.txt'


def get_agent_service_cmd(platform, action):
    # [TODO] Confirm this works with A5
    if platform == WINDOWS:
        return [r'C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe', AGENT_CMD[platform][action]]
    elif platform == MAC:
        return [
            'launchctl', AGENT_CMD[platform][action], '-w',
            '{}/Library/LaunchAgents/com.datadoghq.agent.plist'.format(HOME)
        ]
