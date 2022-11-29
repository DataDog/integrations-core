import cm_client
import packaging.version

from datadog_checks.cloudera.api_client_v7 import ApiClientV7


def make_api_client(check, config):
    cm_client.configuration.username = config.workload_username
    cm_client.configuration.password = config.workload_password
    api_client = cm_client.ApiClient(config.api_url)

    check.log.debug('Getting version from cloudera')
    cloudera_manager_resource_api = cm_client.ClouderaManagerResourceApi(api_client)
    get_version_response = cloudera_manager_resource_api.get_version()
    check.log.debug('get_version_response: %s', get_version_response)
    cloudera_version = get_version_response.version
    check.log.debug('Cloudera Manager Version: %s', cloudera_version)
    cloudera_version = packaging.version.parse(str(cloudera_version))

    # FIXME: For now, no v5 since changes are done in v7
    # if cloudera_version.major == 5:
    # return ApiClientV5(check, api_client)
    if cloudera_version.major == 7:
        return ApiClientV7(check, api_client)
