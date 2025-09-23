# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.api_rest import ApiRest
from datadog_checks.openstack_controller.api.api_sdk import ApiSdk
from datadog_checks.openstack_controller.api.type import ApiType

apis = {
    ApiType.REST: lambda config, logger, http: ApiRest(config, logger, http),
    ApiType.SDK: lambda config, logger, http: ApiSdk(config, logger, http),
}


def make_api(config, logger, http) -> Api:
    logger.debug('creating api object of type `%s`', config.api_type.name)
    return apis[config.api_type](config, logger, http)
