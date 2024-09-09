# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.models.types import copy_raw
from datadog_checks.octopus_deploy.config_models import ConfigMixin

from .constants import API_UP_METRIC, PROJECT_GROUP_COUNT_METRIC, SPACE_COUNT_METRIC
from .spaces import ProjectGroup, Space


class OctopusDeployCheck(AgentCheck, ConfigMixin):

    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)
        self._project_groups_discovery = {}

    def _initialize_caches(self):
        self._initialize_spaces()
        for _, space_name, space, space_config in self.spaces():
            self._initialize_project_groups(space_name, space.id, space_config)

    def _initialize_project_groups(self, space_name, space_id, space_config):
        if space_name not in self._project_groups_discovery:
            normalized_project_groups = normalize_discover_config_include(
                self.log, space_config.get("project_groups") if space_config else None
            )
            self.log.debug("Project groups discovery: %s", normalized_project_groups)
            if normalized_project_groups:
                self._project_groups_discovery[space_name] = Discovery(
                    lambda: self._get_new_project_groups(space_id),
                    limit=space_config.get('project_groups').get('limit') if space_config else None,
                    include=normalized_project_groups,
                    exclude=space_config.get('project_groups').get('exclude') if space_config else None,
                    interval=space_config.get('project_groups').get('interval') if space_config else None,
                    key=lambda project_group: project_group.name,
                )
            else:
                self._project_groups_discovery[space_name] = None
        if self._project_groups_discovery[space_name]:
            discovered_project_groups = list(self._project_groups_discovery[space_name].get_items())
        else:
            discovered_project_groups = [
                (None, project_group.name, project_group, None)
                for project_group in self._get_new_project_groups(space_id)
            ]

        for _, project_group_name, project_group, _ in discovered_project_groups:
            tags = [
                f"project_group_id:{project_group.id}",
                f"project_group_name:{project_group_name}",
                f"space_name:{space_name}",
            ]
            self.gauge(PROJECT_GROUP_COUNT_METRIC, 1, tags=tags)

        self.log.debug("Discovered project groups: %s", discovered_project_groups)

    def _initialize_spaces(self):
        self.spaces_discovery = None
        if self.config.spaces:
            normalized_spaces = normalize_discover_config_include(self.log, self.config.spaces)
            self.log.info("Spaces discovery: %s", self.config.spaces)
            if normalized_spaces:
                self.spaces_discovery = Discovery(
                    lambda: self._get_new_spaces(),
                    limit=self.config.spaces.limit,
                    include=normalized_spaces,
                    exclude=self.config.spaces.exclude,
                    interval=self.config.spaces.interval,
                    key=lambda space: space.name,
                )

    def _get_new_project_groups(self, space_id):
        project_groups_endpoint = f"{self.config.octopus_endpoint}/{space_id}/projectgroups"
        response = self.http.get(project_groups_endpoint)
        response.raise_for_status()
        project_groups_json = response.json().get('Items', [])
        project_groups = []
        for project_group in project_groups_json:
            new_project_group = ProjectGroup(project_group)
            project_groups.append(new_project_group)
        return project_groups

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
            spaces = list(self.spaces_discovery.get_items())
        else:
            spaces = [(None, space.name, space, None) for space in self._get_new_spaces()]

        for _, _, space, _ in spaces:
            tags = [f"space_id:{space.id}", f"space_name:{space.name}", f"space_slug:{space.slug}"]
            self.gauge(SPACE_COUNT_METRIC, 1, tags=tags)

        all_space_names = [space.name for _, _, space, _ in spaces]
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


# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_discover_config_include(log, config):
    normalized_config = {}
    log.debug("normalize_discover_config_include config: %s", config)
    include_list = config.get('include') if isinstance(config, dict) else copy_raw(config.include) if config else []
    log.debug("normalize_discover_config_include include_list: %s", include_list)
    for entry in include_list:
        if isinstance(entry, str):
            normalized_config[entry] = None
        elif isinstance(entry, dict):
            for key, value in entry.items():
                normalized_config[key] = value.copy()
    return normalized_config
