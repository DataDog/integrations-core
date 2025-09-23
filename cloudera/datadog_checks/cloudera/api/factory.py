# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base import ConfigurationError
from datadog_checks.cloudera.api.api import Api
from datadog_checks.cloudera.api.api_v7 import ApiV7
from datadog_checks.cloudera.client.factory import make_client


def make_api(check) -> Api:
    check.log.debug('creating api object')
    client = make_client(
        check.log,
        check.config.cloudera_client,
        **{
            'api_url': check.config.api_url,
            'workload_username': check.shared_config.workload_username,
            'workload_password': check.shared_config.workload_password,
            'pools_size': check.config.pools_size,
            'max_parallel_requests': check.config.max_parallel_requests,
            'verify_ssl': check.config.verify_ssl,
            'ssl_ca_cert': check.config.ssl_ca_cert,
            'cert_file': check.config.cert_file,
            'key_file': check.config.key_file,
        },
    )
    if not client:
        raise ConfigurationError(f'`cloudera_client` is unsupported or unknown: {check.config.cloudera_client}')
    try:
        cloudera_version = client.get_version()
    except Exception:
        check.log.warning(
            "Unable to get the version of Cloudera Manager, please check that the URL is valid and API version "
            "is appended at the end"
        )
        raise
    check.log.debug('cloudera version: %s', cloudera_version)
    if cloudera_version:
        if cloudera_version.major == 7:
            version_raw = str(cloudera_version)
            version_parts = {
                'major': str(cloudera_version.major),
                'minor': str(cloudera_version.minor),
                'patch': str(cloudera_version.micro),
            }
            check.set_metadata('version', version_raw, scheme='parts', part_map=version_parts)
            return ApiV7(check, client)
    raise ConfigurationError(f'Cloudera Manager Version is unsupported or unknown: {cloudera_version}')
