import cm_client
import packaging.version
from cm_client.rest import ApiException

from datadog_checks.cloudera.api_client_v5 import ApiClientV5
from datadog_checks.cloudera.api_client_v7 import ApiClientV7


def make_api_client(check, instance):
    cm_client.configuration.username = instance.get('username', 'cloudera')
    cm_client.configuration.password = instance.get('password', 'cloudera')
    api_host = instance.get('api_host', 'http://localhost')
    api_port = instance.get('api_port', 7180)
    api_version = instance.get('api_version', 'v12')
    api_url = instance.get('api_url')
    # Construct base URL for API
    # http://localhost:7180/api/v12
    if api_url is None:
        api_url = f'{api_host}:{api_port}/api/{api_version}'
    check.log.debug('api_url: %s', api_url)
    api_client = cm_client.ApiClient(api_url)
    try:
        check.log.debug('trying to get version from cloudera')
        cloudera_manager_resource_api = cm_client.ClouderaManagerResourceApi(api_client)
        get_version_response = cloudera_manager_resource_api.get_version()
        check.log.debug('get_version_response: %s', get_version_response)
        cloudera_version = get_version_response.version
        check.log.debug('Cloudera Manager Version: %s', cloudera_version)
        if cloudera_version is not None:
            cloudera_version = packaging.version.parse(str(cloudera_version))
            if cloudera_version.major == 5:
                return ApiClientV5(check, instance, api_client), None
            elif cloudera_version.major == 7:
                return ApiClientV7(check, instance, api_client), None
        return None, f"Cloudera Manager Version not supported: {cloudera_version}"
    except (ApiException, Exception) as e:
        check.log.error('Exception: %s', e)
        return None, str(e)
