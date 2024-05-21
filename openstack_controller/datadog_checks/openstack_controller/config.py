# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from openstack.config import loader

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.models.types import copy_raw
from datadog_checks.openstack_controller.api.type import ApiType


# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_discover_config_include(config, item_keys):
    normalized_config = {}
    include_list = config.get('include') if isinstance(config, dict) else copy_raw(config.include) if config else []
    if include_list:
        if not isinstance(include_list, list):
            raise TypeError('Setting `include` must be an array')
        for entry in include_list:
            if isinstance(entry, str):
                normalized_config[entry] = None
            elif isinstance(entry, dict):
                dict_key = None
                for key in item_keys:
                    if key in entry.keys():
                        normalized_config[entry[key]] = entry
                        break
                if dict_key:
                    normalized_config[dict_key] = entry
            else:
                raise TypeError('`include` entries must be a map or a string')
    return normalized_config


class OpenstackConfig:
    def __init__(self, logger, config):
        self.log = logger
        self.openstack_config_file_path = config.openstack_config_file_path
        self.openstack_cloud_name = config.openstack_cloud_name
        self.keystone_server_url = config.keystone_server_url
        self.username = config.username
        self.password = config.password
        self.domain_id = config.domain_id
        self.user = config.user
        self.nova_microversion = config.nova_microversion
        self.ironic_microversion = config.ironic_microversion
        self.cinder_microversion = config.cinder_microversion
        self.endpoint_interface = config.endpoint_interface
        self.endpoint_region_id = config.endpoint_region_id
        self.paginated_limit = config.paginated_limit
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

        if self.nova_microversion:
            self._validate_microversion(self.nova_microversion, 'nova')

        if self.ironic_microversion:
            self._validate_microversion(self.ironic_microversion, 'ironic')

        if self.cinder_microversion:
            self._validate_microversion(self.cinder_microversion, 'cinder')

    def _validate_microversion(self, microversion, service):
        is_latest = microversion.lower() == 'latest'
        is_float = False
        if is_latest:
            self.log.warning(
                "Setting `%s_microversion` to `latest` is not recommended, see the Openstack documentation "
                "for more details: https://docs.openstack.org/api-guide/compute/microversions.html",
                service,
            )
        try:
            is_float = float(microversion)
        except Exception:
            pass
        if (
            not is_latest
            and not is_float
            and (service != 'cinder' or (service == 'cinder' and 'volume' not in microversion))
        ):
            raise ConfigurationError(
                "Invalid `{}_microversion`: {}; please specify a valid version, see the Openstack documentation"
                "for more details: https://docs.openstack.org/api-guide/compute/microversions.html".format(
                    service, microversion
                ),
            )

    def _validate_user(self):
        if self.username:
            if not self.password:
                raise ConfigurationError("Please specify `password` in your config.")
            self.user = {
                "name": self.username,
                "password": self.password,
                "domain": {"id": self.domain_id},
            }
        else:
            self.log.info("Not detected `username` in config. Searching for legacy `user` config")
            self._validate_user_legacy()
        self.api_type = ApiType.REST

    def _validate_user_legacy(self):
        if self.user is None:
            raise ConfigurationError("Please specify `username` in your config.")
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
        self.username = self.user.get('name')
        self.password = self.user.get('password')
        self.domain_id = self.user.get("domain").get("id")

    def _validate_cloud_config(self):
        self.log.debug("openstack_config_file_path: %s", self.openstack_config_file_path)
        self.log.debug("openstack_cloud_name: %s", self.openstack_cloud_name)
        config = loader.OpenStackConfig(load_envvars=False, config_files=[self.openstack_config_file_path])
        config.get_all_clouds()
        self.api_type = ApiType.SDK
