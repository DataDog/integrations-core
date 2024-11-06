# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.models.types import copy_raw
from datadog_checks.base.utils.time import get_current_datetime

from .config_models import ConfigMixin
from .constants import (
    API_UP_METRIC,
    DEPLOY_COUNT_METRIC,
    DEPLOY_DURATION_METRIC,
    DEPLOY_QUEUE_TIME_METRIC,
    DEPLOY_QUEUED_METRIC,
    DEPLOY_QUEUED_STATE,
    DEPLOY_RERUN_METRIC,
    DEPLOY_RUNNING_METRIC,
    DEPLOY_RUNNING_STATE,
    DEPLOY_SUCCESS_METRIC,
    DEPLOY_WARNINGS_METRIC,
    PROJECT_COUNT_METRIC,
    PROJECT_GROUP_COUNT_METRIC,
    SERVER_COUNT_METRIC,
    SERVER_MAINTENANCE_MODE_METRIC,
    SERVER_MAX_TASKS_METRIC,
)
from .error import handle_error
from .project_groups import Project, ProjectGroup


class OctopusDeployCheck(AgentCheck, ConfigMixin):

    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)
        self._project_groups_discovery = {}
        self._projects_discovery = {}
        self.space_id = None
        space_name = self.instance.get("space")
        self.base_tags = self.instance.get("tags", []) + [f"space_name:{space_name}"]
        self._to_completed_time = None
        self._from_completed_time = None
        self.check_initializations.append(self._get_space_id)
        self.check_initializations.append(self._initialize_caches)

    def _initialize_caches(self):
        self._initialize_project_groups()
        for _, _, project_group, project_group_config in self.project_groups():
            self._initialize_projects(project_group, project_group_config)

    def _update_completed_times(self):
        current_time = get_current_datetime()
        previous_to_time = self._to_completed_time
        self._from_completed_time = previous_to_time if previous_to_time is not None else current_time
        self._to_completed_time = current_time

    def _get_in_progress_tasks(self, project):
        self.log.debug("Getting queued and running tasks for project %s", project.name)
        params = {'project': project.id, 'states': [DEPLOY_QUEUED_STATE, DEPLOY_RUNNING_STATE]}
        url = f"{self.config.octopus_endpoint}/{self.space_id}/tasks"
        response = self.http.get(url, params=params)
        response.raise_for_status()
        tasks_json = response.json().get('Items', [])
        self.log.debug("Found %s in progress tasks for project %s", len(tasks_json), project.name)

        project_tags = project.tags

        any_queued = False
        any_running = False
        for task in tasks_json:
            task_name = task.get("Name")
            state = task.get("State")

            task_tags = [f'task_name:{task_name}', f'task_state:{state}']
            if state == DEPLOY_QUEUED_STATE:
                self.gauge(DEPLOY_QUEUED_METRIC, 1, tags=self.base_tags + project_tags + task_tags)
                any_queued = True
            else:
                self.gauge(DEPLOY_RUNNING_METRIC, 1, tags=self.base_tags + project_tags + task_tags)
                any_running = True

        if not any_queued:
            self.gauge(DEPLOY_QUEUED_METRIC, 0, tags=self.base_tags + project_tags)

        if not any_running:
            self.gauge(DEPLOY_RUNNING_METRIC, 0, tags=self.base_tags + project_tags)

    @handle_error
    def _get_new_completed_tasks_for_project(self, project):
        self.log.debug("Getting new tasks for project %s", project.name)
        params = {
            'project': project.id,
            'fromCompletedDate': self._from_completed_time,
            'toCompletedDate': self._to_completed_time,
        }
        url = f"{self.config.octopus_endpoint}/{self.space_id}/tasks"
        response = self.http.get(url, params=params)
        response.raise_for_status()
        tasks_json = response.json().get('Items', [])
        self.log.debug("Found %s new tasks for project %s", len(tasks_json), project.name)

        project_tags = project.tags

        for task in tasks_json:
            task_id = task.get("Id")
            task_name = task.get("Name")
            state = task.get("State")
            completed_time = task.get("CompletedTime")
            start_time = task.get("StartTime")
            queue_time = task.get("QueueTime")
            can_rerun = int(task.get("CanRerun", False))
            finished_successfully = int(task.get('FinishedSuccessfully', False))
            has_warnings = int(task.get("HasWarningsOrErrors", False))

            self.log.debug("Found completed task id=%s, name=%s", task_id, task_name)

            completed_time_converted = datetime.fromisoformat(completed_time)
            start_time_converted = datetime.fromisoformat(start_time)
            queue_time_converted = datetime.fromisoformat(queue_time)

            duration = completed_time_converted - start_time_converted
            duration_seconds = duration.total_seconds()

            queue_time = start_time_converted - queue_time_converted
            queue_time_seconds = queue_time.total_seconds()

            tags = [f'task_name:{task_name}', f'task_state:{state}']

            self.gauge(DEPLOY_COUNT_METRIC, 1, tags=self.base_tags + project_tags + tags)
            self.gauge(DEPLOY_DURATION_METRIC, duration_seconds, tags=self.base_tags + project_tags + tags)
            self.gauge(DEPLOY_QUEUE_TIME_METRIC, queue_time_seconds, tags=self.base_tags + project_tags + tags)
            self.gauge(DEPLOY_SUCCESS_METRIC, finished_successfully, tags=self.base_tags + project_tags + tags)
            self.gauge(DEPLOY_RERUN_METRIC, can_rerun, tags=self.base_tags + project_tags + tags)
            self.gauge(DEPLOY_WARNINGS_METRIC, has_warnings, tags=self.base_tags + project_tags + tags)

    def _initialize_projects(self, project_group, project_group_config):
        normalized_projects = normalize_discover_config_include(
            self.log, project_group_config.get("projects") if project_group_config else None
        )
        self.log.debug(
            "Projects discovery for project_group %s: %s",
            project_group.name,
            normalized_projects,
        )
        if normalized_projects:
            self._projects_discovery[project_group.name] = Discovery(
                lambda: self._get_new_projects(project_group),
                limit=project_group_config.get('projects').get('limit') if project_group_config else None,
                include=normalized_projects,
                exclude=project_group_config.get('projects').get('exclude') if project_group_config else None,
                interval=(project_group_config.get('projects').get('interval') if project_group_config else None),
                key=lambda project: project.name,
            )
        else:
            self._projects_discovery[project_group.name] = None

        self.log.debug("Discovered projects: %s", self._projects_discovery)

    def _initialize_project_groups(self):
        self._project_groups_discovery = None
        if self.config.project_groups:
            normalized_project_groups = normalize_discover_config_include(self.log, self.config.project_groups)
            self.log.info("Project groups discovery: %s", self.config.project_groups)
            if normalized_project_groups:
                self._project_groups_discovery = Discovery(
                    lambda: self._get_new_project_groups(),
                    limit=self.config.project_groups.limit,
                    include=normalized_project_groups,
                    exclude=self.config.project_groups.exclude,
                    interval=self.config.project_groups.interval,
                    key=lambda project_group: project_group.name,
                )

    def projects(self, project_group):
        if self._projects_discovery.get(project_group.name):
            projects = list(self._projects_discovery[project_group.name].get_items())
        else:
            projects = [(None, project.name, project, None) for project in self._get_new_projects(project_group)]

        return projects

    def collect_project_metrics(self, project_group):
        project_group_tags = [
            f"project_group_id:{project_group.id}",
            f"project_group_name:{project_group.name}",
        ]
        self.gauge(PROJECT_GROUP_COUNT_METRIC, 1, tags=self.base_tags + project_group_tags)

        projects = self.projects(project_group)
        all_project_names = [project.name for _, _, project, _ in projects]
        self.log.info(
            "Collecting data from project group: %s, for projects: %s", project_group.name, ",".join(all_project_names)
        )

        for _, _, project, _ in projects:
            project_tags = [
                f"project_id:{project.id}",
                f"project_name:{project.name}",
            ]
            self.gauge(PROJECT_COUNT_METRIC, 1, tags=self.base_tags + project_group_tags + project_tags)

    def _get_new_projects(self, project_group):
        projects_endpoint = f"{self.config.octopus_endpoint}/{self.space_id}/projectgroups/{project_group.id}/projects"
        response = self.http.get(projects_endpoint)
        response.raise_for_status()
        projects_json = response.json().get('Items', [])
        projects = []
        for project in projects_json:
            new_project = Project(project, project_group)
            projects.append(new_project)
        return projects

    def _get_new_project_groups(self):
        project_groups_endpoint = f"{self.config.octopus_endpoint}/{self.space_id}/projectgroups"
        response = self.http.get(project_groups_endpoint)
        response.raise_for_status()
        project_groups_json = response.json().get('Items', [])
        project_groups = []
        for project_group in project_groups_json:
            new_project_group = ProjectGroup(project_group)
            project_groups.append(new_project_group)

        all_project_group_names = [project_group.name for project_group in project_groups]
        self.log.debug("Found new project groups: %s", all_project_group_names)
        return project_groups

    def _get_space_id(self):
        spaces_endpoint = f"{self.config.octopus_endpoint}/spaces"
        try:
            response = self.http.get(spaces_endpoint)
            response.raise_for_status()
            spaces_json = response.json().get('Items', [])
            for space in spaces_json:
                space_name = space.get("Name")
                if space_name == self.config.space:
                    self.space_id = space.get("Id")
                    self.log.debug("Space id for %s found: %s ", self.config.space, self.space_id)
        except (Timeout, HTTPError, InvalidURL, ConnectionError):
            self.gauge(API_UP_METRIC, 0, tags=self.base_tags)

            raise CheckException(f"Could not connect to octopus API {self.config.octopus_endpoint}octopus_endpoint")

        self.gauge(API_UP_METRIC, 1, tags=self.base_tags)

        if self.space_id is None:
            raise CheckException(f"Space ID not found for provided space name {self.config.space}, does it exist?")

    def project_groups(self):
        if self._project_groups_discovery:
            project_groups = list(self._project_groups_discovery.get_items())
        else:
            project_groups = [
                (None, project_groups.name, project_groups, None) for project_groups in self._get_new_project_groups()
            ]
        return project_groups

    @handle_error
    def collect_server_nodes_metrics(self):
        self.log.debug("Collecting server node metrics.")
        url = f"{self.config.octopus_endpoint}/octopusservernodes"
        response = self.http.get(url)
        response.raise_for_status()
        server_nodes = response.json().get('Items', [])

        for server_node in server_nodes:
            node_id = server_node.get("Id")
            node_name = server_node.get("Name")
            maintenance_mode = int(server_node.get("IsInMaintenanceMode", False))
            max_tasks = int(server_node.get("MaxConcurrentTasks", 0))
            server_tags = [f"server_node_id:{node_id}", f"server_node_name:{node_name}"]

            self.gauge(SERVER_COUNT_METRIC, 1, tags=self.base_tags + server_tags)
            self.gauge(SERVER_MAINTENANCE_MODE_METRIC, maintenance_mode, tags=self.base_tags + server_tags)
            self.gauge(SERVER_MAX_TASKS_METRIC, max_tasks, tags=self.base_tags + server_tags)

    def check(self, _):
        self._update_completed_times()
        for _, _, project_group, _ in self.project_groups():
            self.collect_project_metrics(project_group)
            for _, _, project, _ in self.projects(project_group):
                self._get_new_completed_tasks_for_project(project)
                self._get_in_progress_tasks(project)

        self.collect_server_nodes_metrics()


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
        # entry is dict
        else:
            for key, value in entry.items():
                normalized_config[key] = value.copy()
    return normalized_config
