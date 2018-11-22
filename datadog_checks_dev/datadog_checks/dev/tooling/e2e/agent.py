# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
DEFAULT_AGENT_VERSION = 6

# Must be a certain length
FAKE_API_KEY = 'a' * 32


def get_rate_flag(agent_version):
    if agent_version >= 6:
        return '--check-rate'
    else:
        return 'check_rate'


def get_agent_exe(agent_version, platform='linux'):
    if platform == 'windows':
        return ''
    elif platform == 'mac':
        return ''
    else:
        if agent_version >= 6:
            return '/opt/datadog-agent/bin/agent/agent'
        else:
            return '/opt/datadog-agent/agent/agent.py'


def get_agent_conf_dir(check, agent_version, platform='linux'):
    if platform == 'windows':
        return ''
    elif platform == 'mac':
        return ''
    else:
        if agent_version >= 6:
            return '/etc/datadog-agent/conf.d/{}.d'.format(check)
        else:
            return '/etc/dd-agent/conf.d'
