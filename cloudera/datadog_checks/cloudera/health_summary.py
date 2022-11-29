from datadog_checks.base import AgentCheck

HEALTH_SUMMARY = {
    'DISABLED': AgentCheck.UNKNOWN,
    'HISTORY_NOT_AVAILABLE': AgentCheck.UNKNOWN,
    'NOT_AVAILABLE': AgentCheck.UNKNOWN,
    'GOOD': AgentCheck.OK,
    'CONCERNING': AgentCheck.UNKNOWN,
    'BAD': AgentCheck.CRITICAL,
}
