import cm_client
from cm_client.rest import RESTClientObject
from packaging.version import parse

from datadog_checks.base import ConfigurationError
from datadog_checks.cloudera.api_client_v7 import ApiClientV7


def make_api_client(check, config, shared_config):
    cm_client.configuration.username = shared_config.workload_username
    cm_client.configuration.password = shared_config.workload_password
    api_client = cm_client.ApiClient(config.api_url)
    api_client.rest_client = RESTClientObject(maxsize=(config.max_parallel_requests))
    check.log.debug('Getting version from cloudera API URL: %s', config.api_url)
    cloudera_manager_resource_api = cm_client.ClouderaManagerResourceApi(api_client)
    try:
        get_version_response = cloudera_manager_resource_api.get_version()
    except Exception:
        check.log.warning(
            "Unable to get the version of Cloudera Manager, please check that the URL is valid and API version \
                is appended at the end"
        )
        raise
    check.log.debug('get_version_response: %s', get_version_response)
    response_version = get_version_response.version
    if response_version:
        cloudera_version = parse(response_version)
        check.log.debug('Cloudera Manager Version: %s', cloudera_version)
        if cloudera_version.major == 7:
            version_raw = str(cloudera_version)
            version_parts = {
                'major': str(cloudera_version.major),
                'minor': str(cloudera_version.minor),
                'patch': str(cloudera_version.micro),
            }
            check.set_metadata('version', version_raw, scheme='parts', part_map=version_parts)

            return ApiClientV7(check, api_client)

    raise ConfigurationError(f'Cloudera Manager Version is unsupported or unknown: {response_version}')
