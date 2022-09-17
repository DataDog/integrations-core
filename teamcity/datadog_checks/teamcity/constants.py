# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

from datadog_checks.base import AgentCheck

EVENT_STATUS_MAP = {"SUCCESS": "successful", "FAILURE": "failed"}

SERVICE_CHECK_STATUS_MAP = {
    "SUCCESS": AgentCheck.OK,
    "FAILURE": AgentCheck.CRITICAL,
    "UNKNOWN": AgentCheck.UNKNOWN,
    "NORMAL": AgentCheck.OK,
    "WARNING": AgentCheck.WARNING,
    "ERROR": AgentCheck.CRITICAL,
}

RESOURCE_URL_MAP = {
    "build_configs": "{base_url}/app/rest/buildTypes?locator=project(id:{project_id})",
    "build_config": "{base_url}/app/rest/buildTypes/id:{build_conf}",
    "new_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "started_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "last_build": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},count:1",
    "build_stats": "{base_url}/app/rest/builds/buildId:{build_id}/statistics",
    "agent_usage_stats": "{base_url}/app/rest/builds?locator=agent:(id:{agent_id})&fields=build(id:{build_id},"
    "buildTypeId:{build_conf})",
    "test_occurrences": "{base_url}/app/rest/testOccurrences?locator=build:{build_id}",
    "build_problems": "{base_url}/app/rest/problemOccurrences?locator=build:(id:{build_id})",
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
        self.project_id = None
        self.last_build_id = None


class BuildConfigs(BuildConfig):
    def __init__(self):
        self.build_configs = {}

    def get_build_configs(self):
        return deepcopy(self.build_configs)

    def set_build_config(self, build_type_id, project_id):
        if not self.build_configs.get(build_type_id):
            self.build_configs[build_type_id] = BuildConfig(build_type_id)
            self.build_configs[build_type_id].project_id = project_id

    def get_build_config(self, build_type_id):
        return self.build_configs.get(build_type_id, None)

    def set_last_build_id(self, build_type_id, build_id):
        self.build_configs[build_type_id].last_build_id = build_id

    def get_last_build_id(self, build_type_id):
        build_config = self.build_configs.get(build_type_id, None)
        if build_config:
            return build_config.last_build_id
        return None
