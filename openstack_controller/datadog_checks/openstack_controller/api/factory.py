# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base import ConfigurationError
from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.api_rest import ApiRest


def make_api(logger, instance_config, http) -> Api:
    logger.debug('creating api object')
    logger.debug('instance_config: %s', instance_config)
    openstack_cloud_name = instance_config.get("openstack_cloud_name")
    logger.debug('openstack_cloud_name: %s', openstack_cloud_name)
    if openstack_cloud_name is None:
        keystone_server_url = instance_config.get("keystone_server_url")
        logger.debug('keystone_server_url: %s', keystone_server_url)
        if keystone_server_url is None:
            raise ConfigurationError(
                "Either `keystone_server_url` or `openstack_config_file_path` need to be configured"
            )
        else:
            return _make_rest_api(logger, instance_config, http)
    return None


def _make_rest_api(logger, instance_config, http):
    logger.debug('creating rest api object')
    user = instance_config.get("user")  # backward compatible
    if user is None:
        user_domain = instance_config.get("user_domain", "default")
        user_name = instance_config.get("user_name")
        user_password = instance_config.get("user_password")
        if user_name is None or user_password is None:
            raise ConfigurationError("`user_name` and `user_password` need to be configured")
        return ApiRest(
            logger,
            {
                'keystone_server_url': instance_config.get("keystone_server_url"),
                'user_domain': user_domain,
                'user_name': user_name,
                'user_password': user_password,
            },
            http,
        )
    return None
