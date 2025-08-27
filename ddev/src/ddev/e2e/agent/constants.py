# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class AgentEnvVars:
    API_KEY = 'DD_API_KEY'
    APM_ENABLED = 'DD_APM_ENABLED'
    APP_KEY = 'DD_APP_KEY'
    CMD_PORT = 'DD_CMD_PORT'
    DOGSTATSD_METRICS_STATS = 'DD_DOGSTATSD_METRICS_STATS_ENABLE'
    DOGSTATSD_NON_LOCAL_TRAFFIC = 'DD_DOGSTATSD_NON_LOCAL_TRAFFIC'
    DOGSTATSD_PORT = 'DD_DOGSTATSD_PORT'
    EXPVAR_PORT = 'DD_EXPVAR_PORT'
    HOSTNAME = 'DD_HOSTNAME'
    LOGS_ENABLED = 'DD_LOGS_ENABLED'
    LOGS_URL = 'DD_LOGS_CONFIG_LOGS_DD_URL'
    PROXY_HTTP = 'DD_PROXY_HTTP'
    PROXY_HTTPS = 'DD_PROXY_HTTPS'
    SITE = 'DD_SITE'
    TELEMETRY_ENABLED = 'DD_TELEMETRY_ENABLED'
    URL = 'DD_DD_URL'


# Note: we cannot use pathlib to create the paths as the host running ddev might have a different OS than the VM's OS
# Agent file paths (Linux)
LINUX_AGENT_BIN_PATH = "/opt/datadog-agent/bin/agent/agent"
LINUX_AGENT_PYTHON_PREFIX = "/opt/datadog-agent/embedded/bin/python"
LINUX_AGENT_CONF_DIR = "/etc/datadog-agent/conf.d"
LINUX_SUDOERS_FILE_PATH = "/etc/sudoers.d/dd-agent"

# Agent file paths (Windows)
WINDOWS_AGENT_BIN_PATH = "C:\\Program Files\\Datadog\\Datadog Agent\\bin\\agent.exe"
WINDOWS_AGENT_PYTHON_PREFIX = "C:\\Program Files\\Datadog\\Datadog Agent\\embedded"
WINDOWS_AGENT_CONF_DIR = "C:\\ProgramData\\Datadog\\conf.d"
