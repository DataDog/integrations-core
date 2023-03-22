# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.api_rest import ApiRest
from datadog_checks.openstack_controller.api.type import ApiType


def make_api(api_type, config, logger, http) -> Api:
    logger.debug('creating api object')
    if api_type == ApiType.REST:
        return ApiRest(logger, config, http)
    elif api_type == ApiType.SDK:
        return None
    return None
