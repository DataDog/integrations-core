# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import deepcopy

import requests

from datadog_checks.base import AgentCheck

EVENT_STATUS_MAP = {"SUCCESS": "successful", "FAILURE": "failed"}

SERVICE_CHECK_STATUS_MAP = {"SUCCESS": AgentCheck.OK, "FAILURE": AgentCheck.CRITICAL}

RESOURCE_URL_MAP = {
    "build_configs": "{base_url}/app/rest/buildTypes?locator=project(id:{project_id})",
    "build_config": "{base_url}/app/rest/buildTypes/id:{build_conf}",
    "new_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "started_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "last_build": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},count:1",
    "build_stats": "{base_url}/app/rest/builds/buildType:{build_conf},buildId:{build_id}/statistics",
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
    "tags": ["teamcity:deployment"],
}

BUILD_EVENT = {
    "event_type": "build",
    "msg_title": "Build for {instance_name} {build_status}",
    "msg_text": "Build Number: {build_number}\nDeployed To: {host}\n\nMore Info: {build_webUrl}",
    "tags": ["build"],
}

DEPLOYMENT_EVENT.update(EVENT_BASE)
BUILD_EVENT.update(EVENT_BASE)


def construct_event(is_deployment, instance_name, host, new_build, build_tags):
    build_id = new_build['id']
    build_number = new_build['number']
    build_config = new_build['buildTypeId']
    build_status = EVENT_STATUS_MAP.get(new_build['status'])
    event_tags = deepcopy(build_tags)
    event_tags.extend(['build_id:{}'.format(build_id), 'build_number:{}'.format(build_number)])

    if not instance_name:
        instance_name = build_config

    teamcity_event = deepcopy(DEPLOYMENT_EVENT) if is_deployment else deepcopy(BUILD_EVENT)

    teamcity_event['timestamp'] = int(time.time())
    teamcity_event['msg_title'] = teamcity_event['msg_title'].format(
        instance_name=instance_name, host=host, build_status=build_status
    )
    teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
        build_number=new_build['number'], host=host, build_webUrl=new_build['webUrl']
    )
    teamcity_event['host'] = host
    teamcity_event['tags'].extend(event_tags)

    return teamcity_event


def get_response(check, resource, **kwargs):
    resource_url = RESOURCE_URL_MAP[resource].format(base_url=check.base_url, **kwargs)
    resource_name = " ".join(resource.split("_"))

    try:
        resp = check.http.get(resource_url)
        resp.raise_for_status()

        json_payload = resp.json()
        if resource == 'build_config':
            return json_payload
        elif not json_payload.get("count") or json_payload["count"] == 0:
            check.log.debug("No results found for resource %s url: %s", resource_name, resource_url)
        else:
            check.log.debug("Results found for resource %s url: %s", resource_name, resource_url)
            return json_payload
    except requests.exceptions.HTTPError:
        if resp.status_code == 401:
            check.log.error("Access denied. Enable guest authentication or check user permissions.")
        check.log.exception("Couldn't fetch resource %s, got code %s", resource_name, resp.status_code)
        raise
    except Exception:
        check.log.exception("Couldn't fetch resource %s, unhandled exception", resource_name)
        raise


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
