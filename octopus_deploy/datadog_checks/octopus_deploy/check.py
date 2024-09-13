# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.models.types import copy_raw
from datadog_checks.octopus_deploy.config_models import ConfigMixin

from .constants import API_UP_METRIC, PROJECT_COUNT_METRIC, PROJECT_GROUP_COUNT_METRIC, SPACE_COUNT_METRIC
from .spaces import Project, ProjectGroup, Space


class OctopusDeployCheck(AgentCheck, ConfigMixin):

    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)
        self._project_groups_discovery = {}
        self._projects_discovery = {}

    def _initialize_caches(self):
        self._initialize_spaces()
        for _, space_name, space, space_config in self.spaces():
            self._initialize_project_groups(space_name, space.id, space_config)
            for _, project_group_name, project_group, project_group_config in self.project_groups(space.id, space_name):
                self._initialize_projects(
                    space_name, space.id, project_group_name, project_group.id, project_group_config
                )
                self.projects(space_name, space.id, project_group.id, project_group_name)

    def _initialize_projects(self, space_name, space_id, project_group_name, project_group_id, project_group_config):
        if not self._projects_discovery.get(space_name, {}).get(project_group_name):
            normalized_projects = normalize_discover_config_include(
                self.log, project_group_config.get("projects") if project_group_config else None
            )
            self.log.debug(
                "Projects discovery for space %s project_group %s: %s",
                space_name,
                project_group_name,
                normalized_projects,
            )
            if normalized_projects:
                if not self._projects_discovery.get(space_name):
                    self._projects_discovery[space_name] = {}
                self._projects_discovery[space_name][project_group_name] = Discovery(
                    lambda: self._get_new_projects(space_id, project_group_id),
                    limit=project_group_config.get('projects').get('limit') if project_group_config else None,
                    include=normalized_projects,
                    exclude=project_group_config.get('projects').get('exclude') if project_group_config else None,
                    interval=(project_group_config.get('projects').get('interval') if project_group_config else None),
                    key=lambda project: project.name,
                )
            else:
                if not self._projects_discovery.get(space_name):
                    self._projects_discovery[space_name] = {}

                self._projects_discovery[space_name][project_group_name] = None

        self.log.debug("Discovered projects: %s", self._projects_discovery)

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

        self.log.debug("Discovered project groups: %s", self._project_groups_discovery)

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

    def projects(self, space_name, space_id, project_group_id, project_group_name):
        if self._projects_discovery.get(space_name, {}).get(project_group_name):
            projects = list(self._projects_discovery[space_name][project_group_name].get_items())
        else:
            projects = [
                (None, project.name, project, None) for project in self._get_new_projects(space_id, project_group_id)
            ]

        for _, _, project, _ in projects:
            tags = [
                f"project_id:{project.id}",
                f"project_name:{project.name}",
                f"project_group_id:{project_group_id}",
                f"project_group_name:{project_group_name}",
                f"space_name:{space_name}",
            ]
            self.gauge(PROJECT_COUNT_METRIC, 1, tags=tags)

        all_project_names = [project.name for _, _, project, _ in projects]
        self.log.info("Collecting data from projects: %s", ",".join(all_project_names))
        return projects

    def report_project_metrics(self, project_list, project_group_id, project_group_name, space_name):
        for _, _, project, _ in project_list:
            tags = [
                f"project_id:{project.id}",
                f"project_name:{project.name}",
                f"project_group_id:{project_group_id}",
                f"project_group_name:{project_group_name}",
                f"space_name:{space_name}",
            ]
            self.gauge(PROJECT_COUNT_METRIC, 1, tags=tags)

    def _get_new_projects(self, space_id, project_group_id):
        projects_endpoint = f"{self.config.octopus_endpoint}/{space_id}/projectgroups/{project_group_id}/projects"
        response = self.http.get(projects_endpoint)
        response.raise_for_status()
        projects_json = response.json().get('Items', [])
        projects = []
        for project in projects_json:
            new_project = Project(project)
            projects.append(new_project)
        return projects

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

    def project_groups(self, space_id, space_name):
        if self._project_groups_discovery.get(space_name):
            project_groups = list(self._project_groups_discovery[space_name].get_items())
        else:
            project_groups = [
                (None, project_groups.name, project_groups, None)
                for project_groups in self._get_new_project_groups(space_id)
            ]

        for _, project_group_name, project_group, _ in project_groups:
            tags = [
                f"project_group_id:{project_group.id}",
                f"project_group_name:{project_group_name}",
                f"space_name:{space_name}",
            ]
            self.gauge(PROJECT_GROUP_COUNT_METRIC, 1, tags=tags)

        all_project_group_names = [space.name for _, _, space, _ in project_groups]
        self.log.info("Collecting data from project_groups: %s", ",".join(all_project_group_names))
        return project_groups

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
    if not isinstance(include_list, list):
        raise TypeError('Setting `include` must be an array')
    if len(include_list) == 0:
        return {}
    for entry in include_list:
        if isinstance(entry, str):
            normalized_config[entry] = None
        elif isinstance(entry, dict):
            for key, value in entry.items():
                normalized_config[key] = value.copy()
    return normalized_config
