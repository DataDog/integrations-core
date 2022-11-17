from datadog_checks.base import AgentCheck

# Based on ApiEntityStatus: https://archive.cloudera.com/cm7/7.7.1/generic/jar/cm_api/apidocs/json_ApiEntityStatus.html
API_ENTITY_STATUS = {
    'UNKNOWN': AgentCheck.UNKNOWN,
    'NONE': AgentCheck.UNKNOWN,
    'STOPPED': AgentCheck.UNKNOWN,
    'DOWN': AgentCheck.CRITICAL,
    'UNKNOWN_HEALTH': AgentCheck.UNKNOWN,
    'DISABLED_HEALTH': AgentCheck.CRITICAL,
    'CONCERNING_HEALTH': AgentCheck.WARNING,
    'BAD_HEALTH': AgentCheck.CRITICAL,
    'GOOD_HEALTH': AgentCheck.OK,
    'STARTING': AgentCheck.OK,
    'STOPPING': AgentCheck.OK,
    'HISTORY_NOT_AVAILABLE': AgentCheck.UNKNOWN,
}

CAN_CONNECT = "can_connect"
CLUSTER_HEALTH = "cluster.health"
SERVICE_HEALTH = "service.health"
CLUSTER_RESOURCE_API = "ClusterResourceApi"
SERVICE_RESOURCE_API = "ServiceResourceApi"