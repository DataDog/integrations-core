# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.models.types import copy_raw
from datadog_checks.octopus_deploy.config_models import ConfigMixin

from .constants import API_UP_METRIC, SPACE_COUNT_METRIC
from .spaces import Space


class OctopusDeployCheck(AgentCheck, ConfigMixin):

    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)

    def _initialize_caches(self):
        self.spaces_discovery = None
        if self.config.spaces:
            normalized_spaces = normalize_discover_config_include(self.config.spaces, ["name"])
            self.log.info("Spaces discovery: %s", normalized_spaces)
            if normalized_spaces:
                self.spaces_discovery = Discovery(
                    lambda: self._get_new_spaces(),
                    limit=self.config.spaces.limit,
                    include=normalized_spaces,
                    exclude=self.config.spaces.exclude,
                    interval=self.config.spaces.interval,
                    key=lambda space: space.name,
                )

    def _get_new_spaces(self):
        spaces_endpoint = f"{self.config.octopus_endpoint}/spaces"
        response = self.http.get(spaces_endpoint)
        response.raise_for_status()
        spaces_json = response.json().get('Items', [])
        spaces = []
        for space in spaces_json:
            new_space = Space(space)
            spaces.append(new_space)
        return spaces

    def spaces(self):
        if self.spaces_discovery:
            spaces = [space_discovery[2] for space_discovery in self.spaces_discovery.get_items()]
        else:
            spaces = self._get_new_spaces()

        for space in spaces:
            tags = [f"space_id:{space.id}", f"space_name:{space.name}", f"space_slug:{space.slug}"]
            self.gauge(SPACE_COUNT_METRIC, 1, tags=tags)

        all_space_names = [space.name for space in spaces]
        self.log.info("Collecting data from spaces: %s", ",".join(all_space_names))
        return spaces

    def check(self, _):
        try:
            response = self.http.get(self.config.octopus_endpoint)
            response.raise_for_status()
        except (Timeout, HTTPError, InvalidURL, ConnectionError) as e:
            self.gauge(API_UP_METRIC, 0, tags=self.config.tags)
            self.log.warning(
                "Failed to connect to Octopus Deploy endpoint %s: %s", self.config.octopus_endpoint, str(e)
            )
            raise

        self.gauge(API_UP_METRIC, 1, tags=self.config.tags)
        self._initialize_caches()
        self.spaces()


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
