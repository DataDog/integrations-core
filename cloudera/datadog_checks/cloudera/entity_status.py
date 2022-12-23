from datadog_checks.base.constants import ServiceCheck

# Based on ApiEntityStatus: https://archive.cloudera.com/cm7/7.7.1/generic/jar/cm_api/apidocs/json_ApiEntityStatus.html
ENTITY_STATUS = {
    'GOOD_HEALTH': ServiceCheck.OK,
    'STARTING': ServiceCheck.OK,
    'STOPPING': ServiceCheck.WARNING,
    'CONCERNING_HEALTH': ServiceCheck.WARNING,
    'DOWN': ServiceCheck.CRITICAL,
    'DISABLED_HEALTH': ServiceCheck.CRITICAL,
    'BAD_HEALTH': ServiceCheck.CRITICAL,
    'STOPPED': ServiceCheck.CRITICAL,
    'UNKNOWN_HEALTH': ServiceCheck.UNKNOWN,
    'HISTORY_NOT_AVAILABLE': ServiceCheck.UNKNOWN,
    'UNKNOWN': ServiceCheck.UNKNOWN,
    'NONE': ServiceCheck.UNKNOWN,
}
