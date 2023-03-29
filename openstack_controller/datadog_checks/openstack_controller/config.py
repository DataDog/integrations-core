# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from openstack.config.loader import OpenStackConfig as OpenStackSdkConfig

from datadog_checks.base import ConfigurationError
from datadog_checks.openstack_controller.api.type import ApiType


class OpenstackConfig:
    def __init__(self, logger, instance):
        self.log = logger
        self.instance = instance
        self.openstack_config_file_path = instance.get("openstack_config_file_path")
        self.openstack_cloud_name = instance.get("openstack_cloud_name")
        self.keystone_server_url = instance.get("keystone_server_url")
        self.user_name = instance.get("user_name")
        self.user_password = instance.get("user_password")
        self.domain_id = instance.get("domain_id", "default")
        self.user = instance.get("user")
        self.nova_microversion = instance.get('nova_microversion')
        self.api_type = None
        self.validate()

    def validate(self):
        self.log.info("Validating config")
        if not self.openstack_config_file_path and not self.keystone_server_url:
            raise ConfigurationError("Either keystone_server_url or openstack_config_file_path need to be provided.")
        if self.openstack_config_file_path:
            self._validate_cloud_config()
        else:
            self._validate_user()

    def _validate_user(self):
        if self.user_name:
            if not self.user_password:
                raise ConfigurationError("Please specify `user_password` in your config.")
            self.user = {
                "name": self.user_name,
                "password": self.user_password,
                "domain": {"id": self.domain_id},
            }
        else:
            self.log.info("Not detected `user_name` in config. Searching for legacy `user` config")
            self._validate_user_legacy()
        self.api_type = ApiType.REST

    def _validate_user_legacy(self):
        if self.user is None:
            raise ConfigurationError("Please specify `user_name` in your config.")
        if not (
            self.user.get('name')
            and self.user.get('password')
            and self.user.get("domain")
            and self.user.get("domain").get("id")
        ):
            raise ConfigurationError(
                'The user should look like: '
                '{"name": "my_name", "password": "my_password", "domain": {"id": "my_domain_id"}}'
            )

    def _validate_cloud_config(self):
        self.log.debug("openstack_config_file_path: %s", self.openstack_config_file_path)
        self.log.debug("openstack_cloud_name: %s", self.openstack_cloud_name)
        config = OpenStackSdkConfig(load_envvars=False, config_files=[self.openstack_config_file_path])
        config.get_all_clouds()
        config.get_one(cloud=self.openstack_cloud_name)
        self.api_type = ApiType.SDK
