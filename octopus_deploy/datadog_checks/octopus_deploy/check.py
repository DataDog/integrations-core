# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
from collections.abc import Iterable

from cachetools import TTLCache
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.discovery.discovery import Discovery
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp
from datadog_checks.octopus_deploy.config_models.instance import ProjectGroups, Projects

from .config_models import ConfigMixin

TTL_CACHE_MAXSIZE = 50
TTL_CACHE_TTL = 3600

EVENT_TO_ALERT_TYPE = {
    'MachineHealthy': 'success',
    'MachineUnhealthy': 'warning',
    'MachineUnavailable': 'warning',
    'CertificateExpired': 'error',
    'DeploymentFailed': 'error',
    'DeploymentSucceeded': 'success',
    'LoginFailed': 'warning',
    'MachineAdded': 'info',
    'MachineDeleted': 'info',
}


class OctopusDeployCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)
        self._from_completed_time = None
        self._to_completed_time = None
        self.current_datetime = None
        self._spaces_discovery = None
        self._default_project_groups_discovery = {}
        self._project_groups_discovery = {}
        self._default_projects_discovery = {}
        self._projects_discovery = {}
        self._environments_discovery = {}
        self._environments_cache = {}
        self._deployments_cache = TTLCache(maxsize=TTL_CACHE_MAXSIZE, ttl=TTL_CACHE_TTL)
        self._releases_cache = TTLCache(maxsize=TTL_CACHE_MAXSIZE, ttl=TTL_CACHE_TTL)
        endpoint = self.instance.get("octopus_endpoint")
        octopus_server_tag = [f"octopus_server:{endpoint}"]
        self._base_tags = self.instance.get("tags", []) + octopus_server_tag
        self.collect_events = self.instance.get("collect_events", False)

    def check(self, _):
        self._update_times()
        self._process_spaces()
        self._collect_server_nodes_metrics()

    def _update_times(self):
        self.current_datetime = get_current_datetime()
        self._from_completed_time = (
            self._to_completed_time if self._to_completed_time is not None else self.current_datetime
        )
        self._to_completed_time = self.current_datetime

    def _process_endpoint(self, endpoint, params=None, report_service_check=False):
        try:
            params = {} if params is None else params
            response = self.http.get(f"{self.config.octopus_endpoint}/{endpoint}", params=params)
            response.raise_for_status()
            if report_service_check:
                self.gauge('api.can_connect', 1, tags=self._base_tags)
            return response.json()
        except (Timeout, HTTPError, InvalidURL, ConnectionError) as e:
            if report_service_check:
                self.gauge('api.can_connect', 0, tags=self._base_tags)
                raise CheckException(
                    f"Could not connect to octopus API {self.config.octopus_endpoint} octopus_endpoint: {e}"
                ) from e
            else:
                self.warning("Failed to access endpoint: %s: %s", endpoint, e)
                return {}

    def _process_paginated_endpoint(self, endpoint, params=None, report_service_check=False):
        skip = 0
        take = self.config.paginated_limit
        num_pages = 1
        num_pages_seen = 0
        all_items = []
        params = {} if params is None else params
        while num_pages_seen < num_pages:
            params['skip'] = skip
            params['take'] = take

            response_json = self._process_endpoint(endpoint, params=params, report_service_check=report_service_check)
            if response_json == {}:
                return response_json
            items = response_json.get("Items")
            num_pages_seen += 1
            num_pages = response_json.get("NumberOfPages", num_pages)
            skip += self.config.paginated_limit
            all_items = all_items + items
        return {"Items": all_items}

    def _init_spaces_discovery(self):
        self.log.info("Spaces discovery: %s", self.config.spaces)
        self._spaces_discovery = Discovery(
            lambda: self._process_paginated_endpoint("api/spaces", report_service_check=True).get('Items', []),
            limit=self.config.spaces.limit,
            include=normalize_discover_config_include(self.config.spaces),
            exclude=self.config.spaces.exclude,
            interval=self.config.spaces.interval,
            key=lambda space: space.get("Name"),
        )

    def _init_default_project_groups_discovery(self, space_id):
        self.log.info("Default Project Groups discovery: %s", self.config.project_groups)
        if space_id not in self._default_project_groups_discovery:
            self._default_project_groups_discovery[space_id] = Discovery(
                lambda: self._process_paginated_endpoint(
                    f"api/{space_id}/projectgroups", report_service_check=True
                ).get('Items', []),
                limit=self.config.project_groups.limit,
                include=normalize_discover_config_include(self.config.project_groups),
                exclude=self.config.project_groups.exclude,
                interval=self.config.project_groups.interval,
                key=lambda project_group: project_group.get("Name"),
            )

    def _init_project_groups_discovery(self, space_id, project_groups_config):
        self.log.info("Project Groups discovery: %s", project_groups_config)
        if space_id not in self._project_groups_discovery:
            self._project_groups_discovery[space_id] = Discovery(
                lambda: self._process_paginated_endpoint(
                    f"api/{space_id}/projectgroups", report_service_check=True
                ).get('Items', []),
                limit=project_groups_config.limit,
                include=normalize_discover_config_include(project_groups_config),
                exclude=project_groups_config.exclude,
                interval=project_groups_config.interval,
                key=lambda project_group: project_group.get("Name"),
            )

    def _init_default_projects_discovery(self, space_id, project_group_id):
        self.log.info("Default Projects discovery: %s", self.config.projects)
        if space_id not in self._default_projects_discovery:
            self._default_projects_discovery[space_id] = {}
        if project_group_id not in self._default_projects_discovery[space_id]:
            self._default_projects_discovery[space_id][project_group_id] = Discovery(
                lambda: self._process_paginated_endpoint(
                    f"api/{space_id}/projectgroups/{project_group_id}/projects",
                    report_service_check=True,
                ).get('Items', []),
                limit=self.config.projects.limit,
                include=normalize_discover_config_include(self.config.projects),
                exclude=self.config.projects.exclude,
                interval=self.config.projects.interval,
                key=lambda project: project.get("Name"),
            )

    def _init_projects_discovery(self, space_id, project_group_id, projects_config):
        self.log.info("Projects discovery: %s", projects_config)
        if space_id not in self._projects_discovery:
            self._projects_discovery[space_id] = {}
        if project_group_id not in self._projects_discovery[space_id]:
            self._projects_discovery[space_id][project_group_id] = Discovery(
                lambda: self._process_paginated_endpoint(
                    f"api/{space_id}/projectgroups/{project_group_id}/projects",
                    report_service_check=True,
                ).get('Items', []),
                limit=projects_config.limit,
                include=normalize_discover_config_include(projects_config),
                exclude=projects_config.exclude,
                interval=projects_config.interval,
                key=lambda project: project.get("Name"),
            )

    def _process_spaces(self):
        if self.config.spaces:
            if self._spaces_discovery is None:
                self._init_spaces_discovery()
            spaces = list(self._spaces_discovery.get_items())
        else:
            spaces = [
                (None, space.get("Name"), space, None)
                for space in self._process_paginated_endpoint("api/spaces", report_service_check=True).get('Items', [])
            ]
        self.log.debug("Monitoring %s spaces", len(spaces))
        for _, _, space, space_config in spaces:
            space_id = space.get("Id")
            space_name = space.get("Name")
            tags = self._base_tags + [f'space_id:{space_id}', f'space_name:{space_name}']
            self.gauge("space.count", 1, tags=tags)
            self.log.debug("Processing space %s", space_name)
            self._process_environments(space_id, space_name)
            self._process_project_groups(
                space_id, space_name, space_config.get("project_groups") if space_config else None
            )
            self._collect_machine_metrics(space_id)
            if self.collect_events:
                self._collect_new_events(space_id, space_name)

    def _process_project_groups(self, space_id, space_name, project_groups_config):
        if project_groups_config:
            self._init_project_groups_discovery(space_id, ProjectGroups(**project_groups_config))
            project_groups = list(self._project_groups_discovery[space_id].get_items())
        else:
            if self.config.project_groups:
                self._init_default_project_groups_discovery(space_id)
                project_groups = list(self._default_project_groups_discovery[space_id].get_items())
            else:
                project_groups = [
                    (None, project_group.get("Name"), project_group, None)
                    for project_group in self._process_paginated_endpoint(f"api/{space_id}/projectgroups").get(
                        'Items', []
                    )
                ]
        self.log.debug("Monitoring %s Project Groups", len(project_groups))
        for _, _, project_group, project_group_config in project_groups:
            project_group_id = project_group.get("Id")
            project_group_name = project_group.get("Name")
            tags = self._base_tags + [
                f'space_name:{space_name}',
                f'project_group_id:{project_group_id}',
                f'project_group_name:{project_group_name}',
            ]
            self.gauge("project_group.count", 1, tags=tags)
            self._process_projects(
                space_id,
                space_name,
                project_group_id,
                project_group_name,
                project_group_config.get("projects") if project_group_config else None,
            )

    def _process_projects(self, space_id, space_name, project_group_id, project_group_name, projects_config):
        if projects_config:
            self._init_projects_discovery(space_id, project_group_id, Projects(**projects_config))
            projects = list(self._projects_discovery[space_id][project_group_id].get_items())
        else:
            if self.config.projects:
                self._init_default_projects_discovery(space_id, project_group_id)
                projects = list(self._default_projects_discovery[space_id][project_group_id].get_items())
            else:
                projects = [
                    (None, project.get("Name"), project, None)
                    for project in self._process_paginated_endpoint(
                        f"api/{space_id}/projectgroups/{project_group_id}/projects"
                    ).get('Items', [])
                ]
        self.log.debug("Monitoring %s Projects for %s in %s", len(projects), project_group_name, space_name)
        for _, _, project, _ in projects:
            project_id = project.get("Id")
            project_name = project.get("Name")
            tags = self._base_tags + [
                f'space_name:{space_name}',
                f'project_group_name:{project_group_name}',
                f'project_id:{project_id}',
                f'project_name:{project_name}',
            ]
            if not self.config.disable_generic_tags and self.config.unified_service_tagging:
                tags.append(f'service:{project_name}')
            self.gauge("project.count", 1, tags=tags)
            self._process_queued_and_running_tasks(space_id, space_name, project_id, project_name)
            self._process_completed_tasks(space_id, space_name, project_id, project_name)

    def _process_environments(self, space_id, space_name):
        if self.config.environments:
            self._init_environments_discovery(space_id)
            environments = list(self._environments_discovery[space_id].get_items())
        else:
            environments = [
                (None, environment.get("Name"), environment, None)
                for environment in self._process_paginated_endpoint(f"api/{space_id}/environments").get('Items', [])
            ]

        self.log.debug("Collecting %s environments for %s", len(environments), space_name)

        for _, _, environment, _ in environments:
            environment_name = environment.get("Name")
            environment_slug = environment.get("Slug")
            environment_id = environment.get("Id")
            self._environments_cache[environment_id] = environment_name
            use_guided_failure = int(environment.get("UseGuidedFailure", False))
            allow_dynamic_infrastructure = int(environment.get("AllowDynamicInfrastructure", False))

            tags = self._base_tags + [
                f"space_name:{space_name}",
                f"environment_name:{environment_name}",
                f"environment_id:{environment_id}",
                f"environment_slug:{environment_slug}",
            ]
            if not self.config.disable_generic_tags and self.config.unified_service_tagging:
                tags.append(f'env:{environment_name}')
            self.gauge("environment.count", 1, tags=tags)
            self.gauge("environment.use_guided_failure", use_guided_failure, tags=tags)
            self.gauge("environment.allow_dynamic_infrastructure", allow_dynamic_infrastructure, tags=tags)

    def _init_environments_discovery(self, space_id):
        self.log.info("Default Environments discovery: %s", self.config.environments)
        if space_id not in self._environments_discovery:
            self._environments_discovery[space_id] = Discovery(
                lambda: self._process_paginated_endpoint(f"api/{space_id}/environments").get('Items', []),
                limit=self.config.environments.limit,
                include=normalize_discover_config_include(self.config.environments),
                exclude=self.config.environments.exclude,
                interval=self.config.environments.interval,
                key=lambda environment: environment.get("Name"),
            )

    def _process_queued_and_running_tasks(self, space_id, space_name, project_id, project_name):
        self.log.debug("Collecting running and queued tasks for project %s", project_name)
        params = {'name': 'Deploy', 'project': project_id, 'states': ["Queued", "Executing"]}
        response_json = self._process_paginated_endpoint(f"api/{space_id}/tasks", params)
        self._process_tasks(space_id, space_name, project_name, response_json.get('Items', []))

    def _process_completed_tasks(self, space_id, space_name, project_id, project_name):
        self.log.debug("Collecting completed tasks for project %s", project_name)
        params = {
            'name': 'Deploy',
            'project': project_id,
            'fromCompletedDate': self._from_completed_time,
            'toCompletedDate': self._to_completed_time,
        }
        response_json = self._process_paginated_endpoint(f"api/{space_id}/tasks", params)
        self._process_tasks(space_id, space_name, project_name, response_json.get('Items', []))

    def _calculate_task_times(self, task):
        task_queue_time = task.get("QueueTime")
        task_start_time = task.get("StartTime")
        task_completed_time = task.get("CompletedTime")
        if task_start_time:
            queued_time = (
                datetime.datetime.fromisoformat(task_start_time) - datetime.datetime.fromisoformat(task_queue_time)
            ).total_seconds()
            if task_completed_time:
                executing_time = (
                    datetime.datetime.fromisoformat(task_completed_time)
                    - datetime.datetime.fromisoformat(task_start_time)
                ).total_seconds()
                completed_time = (
                    self.current_datetime - datetime.datetime.fromisoformat(task_completed_time)
                ).total_seconds()
            else:
                executing_time = (
                    self.current_datetime - datetime.datetime.fromisoformat(task_start_time)
                ).total_seconds()
                completed_time = -1
        else:
            queued_time = (self.current_datetime - datetime.datetime.fromisoformat(task_queue_time)).total_seconds()
            executing_time = -1
            completed_time = -1
        return queued_time, executing_time, completed_time

    def _process_tasks(self, space_id, space_name, project_name, tasks_json):
        self.log.debug("Discovered %s tasks for project %s", len(tasks_json), project_name)
        for task in tasks_json:
            task_id = task.get("Id")
            server_node = task.get("ServerNode")
            task_state = task.get("State")
            pending_interruptions = task.get("HasPendingInterruptions")
            is_queued = task_state == "Queued"
            is_executing = task_state == "Executing"
            deployment_id = task.get("Arguments", {}).get("DeploymentId")
            environment_name, deployment_tags = self._get_deployment_tags(space_id, deployment_id)
            if environment_name in self._environments_cache.values():
                tags = (
                    self._base_tags
                    + deployment_tags
                    + [
                        f'space_name:{space_name}',
                        f'project_name:{project_name}',
                        f'task_state:{task_state}',
                        f'server_node:{server_node}',
                    ]
                )
                if not self.config.disable_generic_tags and self.config.unified_service_tagging:
                    tags.append(f'service:{project_name}')
                self.log.debug("Processing task id %s for project %s", task_id, project_name)
                queued_time, executing_time, completed_time = self._calculate_task_times(task)
                self.gauge("deployment.count", 1, tags=tags)
                self.gauge("deployment.waiting", pending_interruptions, tags=tags)
                self.gauge("deployment.queued", is_queued, tags=tags)
                self.gauge("deployment.executing", is_executing, tags=tags)
                self.gauge("deployment.queued_time", queued_time, tags=tags)
                if executing_time != -1:
                    self.gauge("deployment.executing_time", executing_time, tags=tags)
                if completed_time != -1:
                    self.gauge("deployment.completed_time", completed_time, tags=tags)

                    if self.logs_enabled:
                        self.log.debug("Collecting logs for task id: %s", task_id)
                        self._collect_deployment_logs(space_id, task_id, tags)
            else:
                self.log.debug(
                    "Skipping task id: %s for project %s in skipped environment: %s",
                    task_id,
                    project_name,
                    environment_name,
                )

    def _get_deployment_tags(self, space_id, deployment_id):
        self.log.debug("Getting deployment tags for deployment id: %s", deployment_id)
        cached_deployment = self._deployments_cache.get(deployment_id)

        if cached_deployment is not None:
            release_version = cached_deployment[0]
            environment_name = cached_deployment[1]
        else:
            self.log.debug("Cached deployment not found for deployment id: %s", deployment_id)
            deployment = self._process_endpoint(f"api/{space_id}/deployments/{deployment_id}")
            release_id = deployment.get("ReleaseId")
            environment_id = deployment.get("EnvironmentId")
            environment_name = self._environments_cache.get(environment_id)
            release_version = self._releases_cache.get(release_id)
            if release_version is None:
                self.log.debug(
                    "Cached release not found for deployment id: %s, release id: %s", deployment_id, release_id
                )
                release = self._process_endpoint(f"api/{space_id}/releases/{release_id}")
                release_version = release.get("Version")
                self._releases_cache[release_id] = release_version

            self._deployments_cache[deployment_id] = (release_version, environment_name)

        tags = [
            f'deployment_id:{deployment_id}',
            f'release_version:{release_version}',
            f'environment_name:{environment_name}',
        ]
        if not self.config.disable_generic_tags and self.config.unified_service_tagging:
            tags.append(f'env:{environment_name}')
            tags.append(f'version:{release_version}')

        return environment_name, tags

    def _collect_server_nodes_metrics(self):
        self.log.debug("Collecting server node metrics.")
        url = "api/octopusservernodes"
        response_json = self._process_paginated_endpoint(url)
        server_nodes = response_json.get('Items', [])

        for server_node in server_nodes:
            node_id = server_node.get("Id")
            node_name = server_node.get("Name")
            maintenance_mode = int(server_node.get("IsInMaintenanceMode", False))
            max_tasks = int(server_node.get("MaxConcurrentTasks", 0))
            server_tags = [f"server_node_id:{node_id}", f"server_node_name:{node_name}"]
            self.gauge("server_node.count", 1, tags=self._base_tags + server_tags)
            self.gauge("server_node.in_maintenance_mode", maintenance_mode, tags=self._base_tags + server_tags)
            self.gauge("server_node.max_concurrent_tasks", max_tasks, tags=self._base_tags + server_tags)

    def _collect_machine_metrics(self, space_id):
        self.log.debug("Collecting server node metrics.")
        url = f"api/{space_id}/machines"
        response_json = self._process_paginated_endpoint(url)
        machines = response_json.get('Items', [])

        for machine in machines:
            machine_id = machine.get("Id")
            machine_name = machine.get("Name")
            machine_slug = machine.get("Slug")
            roles = machine.get("Roles", [])
            os = machine.get("OperatingSystem")
            health_status = machine.get("HealthStatus")
            is_healthy = health_status.startswith("Healthy")
            machine_tags = [
                f"machine_id:{machine_id}",
                f"machine_name:{machine_name}",
                f"machine_slug:{machine_slug}",
                f"health_status:{health_status}",
                f"operating_system:{os}",
            ]
            machine_tags += roles
            environment_ids = machine.get("EnvironmentIds")
            env_tags = []
            for env_id in environment_ids:
                env_name = self._environments_cache.get(env_id)
                env_tag_name = (
                    "env"
                    if not self.config.disable_generic_tags and self.config.unified_service_tagging
                    else "environment_name"
                )
                env_tags.append(f"{env_tag_name}:{env_name}")
            machine_tags += env_tags
            self.gauge("machine.count", 1, tags=self._base_tags + machine_tags)
            self.gauge("machine.is_healthy", is_healthy, tags=self._base_tags + machine_tags)

    def _collect_deployment_logs(self, space_id, task_id, tags):
        url = f"api/{space_id}/tasks/{task_id}/details"
        activity_logs = self._process_endpoint(url).get('ActivityLogs', [])
        self._submit_activity_logs(activity_logs, tags)

    def _submit_activity_logs(self, activity_logs, tags):
        for log in activity_logs:
            name = log.get("Name")
            log_elements = log.get("LogElements", [])
            children = log.get("Children", [])

            for log_element in log_elements:
                payload = {}
                payload['ddtags'] = ",".join(tags)
                payload['message'] = log_element.get("MessageText")
                payload['timestamp'] = get_timestamp(datetime.datetime.fromisoformat(log_element.get("OccurredAt")))
                payload['status'] = log_element.get("Category")
                payload['stage_name'] = name
                self.send_log(payload)

            self._submit_activity_logs(children, tags)

    def _collect_new_events(self, space_id, space_name):
        self.log.debug("Collecting events for space id %s: name %s", space_id, space_name)
        url = f"api/{space_id}/events"
        params = {
            'from': self._from_completed_time,
            'to': self._to_completed_time,
            'eventCategories': list(EVENT_TO_ALERT_TYPE.keys()),
        }
        events = self._process_paginated_endpoint(url, params=params).get('Items', [])
        tags = self._base_tags + [f"space_name:{space_name}"]

        for event in events:
            timestamp = datetime.datetime.fromisoformat(event.get("Occurred")).timestamp()
            category = event.get("Category")
            title = f"Octopus Deploy: {category}"
            event_message = event.get("Message")
            event = {
                'timestamp': timestamp,
                'event_type': self.__NAMESPACE__,
                'host': self.hostname,
                'msg_text': event_message,
                'msg_title': title,
                'alert_type': EVENT_TO_ALERT_TYPE[category],
                'source_type_name': self.__NAMESPACE__,
                'tags': tags,
            }
            self.event(event)


# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_discover_config_include(config):
    normalized_config = {}
    include_list = (
        list(getattr(config, 'include', [])) if isinstance(getattr(config, 'include', None), Iterable) else []
    )
    if len(include_list) == 0:
        return {}
    for entry in include_list:
        if isinstance(entry, str):
            normalized_config[entry] = None
        elif hasattr(entry, 'items'):
            for key, value in entry.items():
                normalized_config[key] = value.copy()
    return normalized_config
