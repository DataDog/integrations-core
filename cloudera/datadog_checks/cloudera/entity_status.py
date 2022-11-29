from datadog_checks.base import AgentCheck

ENTITY_STATUS = {
    'UNKNOWN': AgentCheck.UNKNOWN,
    'NONE': AgentCheck.UNKNOWN,
    'STOPPED': AgentCheck.UNKNOWN,
    'DOWN': AgentCheck.UNKNOWN,
    'UNKNOWN_HEALTH': AgentCheck.UNKNOWN,
    'DISABLED_HEALTH': AgentCheck.UNKNOWN,
    'CONCERNING_HEALTH': AgentCheck.UNKNOWN,
    'BAD_HEALTH': AgentCheck.CRITICAL,
    'GOOD_HEALTH': AgentCheck.OK,
    'STARTING': AgentCheck.UNKNOWN,
    'STOPPING': AgentCheck.UNKNOWN,
    'HISTORY_NOT_AVAILABLE': AgentCheck.UNKNOWN,
}
