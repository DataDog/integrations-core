# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from datadog_checks.base import AgentCheck

SERVICE_CHECK_BUILD_STATUS = 'build.status'
SERVICE_CHECK_BUILD_PROBLEMS = 'build.problems'
SERVICE_CHECK_TEST_RESULTS = 'test.results'
SERVICE_CHECK_OPENMETRICS = 'teamcity.openmetrics.health'

DEFAULT_BUILD_CONFIGS_LIMIT = 5

STATUS_MAP = {
    "SUCCESS": {"check_status": AgentCheck.OK, "msg_title": "successful", "alert_type": "success"},
    "FAILURE": {"check_status": AgentCheck.CRITICAL, "msg_title": "failed", "alert_type": "error"},
    "UNKNOWN": {"check_status": AgentCheck.UNKNOWN},
    "NORMAL": {"check_status": AgentCheck.OK},
    "WARNING": {"check_status": AgentCheck.WARNING},
    "ERROR": {"check_status": AgentCheck.CRITICAL},
}

RESOURCE_URL_MAP = {
    "build_configs": "{base_url}/app/rest/buildTypes?locator=project(id:{project_id})",
    "build_config": "{base_url}/app/rest/buildTypes/id:{build_conf}",
    "new_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "started_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "last_build": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},project:{project_id},count:1",
    "build_stats": "{base_url}/app/rest/builds/buildId:{build_id}/statistics",
    "agent_usage_stats": "{base_url}/app/rest/builds?locator=agent:(id:{agent_id})&fields=build(id:{build_id},"
    "buildTypeId:{build_conf})",
    "test_occurrences": "{base_url}/app/rest/testOccurrences?locator=build:{build_id}",
    "build_problems": "{base_url}/app/rest/problemOccurrences?locator=build:(id:{build_id})",
    "build_config_settings": "{base_url}/app/rest/buildTypes/id:{build_conf}/settings",
    "teamcity_server_details": "{base_url}/app/rest/server",
}

EVENT_BASE = {"timestamp": None, "source_type_name": "teamcity", "host": None, "tags": []}

DEPLOYMENT_EVENT = {
    "event_type": "teamcity_deployment",
    "msg_title": "{instance_name} deployed to {host} {build_status}",
    "msg_text": "Build Number: {build_number}\n\nMore Info: {build_webUrl}",
    "tags": [],
}

BUILD_EVENT = {
    "event_type": "build",
    "msg_title": "Build for {instance_name} {build_status}",
    "msg_text": "Build Number: {build_number}\nDeployed To: {host}\n\nMore Info: {build_webUrl}",
    "tags": [],
}

DEPLOYMENT_EVENT.update(EVENT_BASE)
BUILD_EVENT.update(EVENT_BASE)


class Build(object):
    def __init__(self, build_id):
        self.build_id = build_id


class BuildConfig(object):
    def __init__(self, build_config_id):
        self.build_config_id = build_config_id
        self.last_build_id = None
        self.build_config_type = None

    def get(self, attribute, default=None):
        if attribute in self:
            return self.getattr(attribute)
        else:
            return default


class BuildConfigs(BuildConfig):
    def __init__(self):
        self.build_configs = {}

    def get_build_configs(self, project_id):
        if self.build_configs.get(project_id):
            return deepcopy(self.build_configs[project_id])

    def set_build_config(self, project_id, build_config_id, build_config_type=None):
        if not self.build_configs.get(project_id):
            self.build_configs[project_id] = {}
            self.build_configs[project_id][build_config_id] = BuildConfig(build_config_id)
        else:
            if build_config_id not in self.build_configs[project_id]:
                self.build_configs[project_id][build_config_id] = BuildConfig(build_config_id)
        if build_config_type:
            self.build_configs[project_id][build_config_id].build_config_type = build_config_type

    def get_build_config(self, project_id, build_config_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project:
            return stored_project.get(build_config_id, None)

    def set_last_build_id(self, project_id, build_config_id, build_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project and stored_project.get(build_config_id):
            self.build_configs[project_id][build_config_id].last_build_id = build_id

    def get_last_build_id(self, project_id, build_config_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project and stored_project.get(build_config_id):
            build_config = stored_project.get(build_config_id, None)
            if build_config:
                return build_config.last_build_id
        return None
