from datadog_checks.base import AgentCheck

# Based on ApiEntityStatus: https://archive.cloudera.com/cm7/7.7.1/generic/jar/cm_api/apidocs/json_ApiEntityStatus.html
ENTITY_STATUS = {
    'GOOD_HEALTH': AgentCheck.OK,
    'STARTING': AgentCheck.OK,
    'STOPPING': AgentCheck.WARNING,
    'CONCERNING_HEALTH': AgentCheck.WARNING,
    'DOWN': AgentCheck.CRITICAL,
    'DISABLED_HEALTH': AgentCheck.CRITICAL,
    'BAD_HEALTH': AgentCheck.CRITICAL,
    'STOPPED': AgentCheck.CRITICAL,
    'UNKNOWN_HEALTH': AgentCheck.UNKNOWN,
    'HISTORY_NOT_AVAILABLE': AgentCheck.UNKNOWN,
    'UNKNOWN': AgentCheck.UNKNOWN,
    'NONE': AgentCheck.UNKNOWN,
}
