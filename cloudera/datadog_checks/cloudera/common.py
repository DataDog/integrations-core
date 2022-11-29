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
ROLE_HEALTH = "role.health"
HOST_HEALTH = "host.health"
CLUSTERS_RESOURCE_API = "ClustersResourceApi"
SERVICES_RESOURCE_API = "ServicesResourceApi"

# mock all of the methods and classes of the cloudera client
