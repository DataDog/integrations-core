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
    "all_builds": {"url": "{base_url}/app/rest/buildTypes", "name": "all build configurations"},
    "new_builds": {
        "url": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},state:finished",
        "name": "new builds",
    },
    "last_build": {"url": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},count:1", "name": "last build"},
    "build_stats": {
        "url": "{base_url}/app/rest/builds/buildType:{build_conf},buildId:{build_id}/statistics",
        "name": "build configuration statistics",
    },
    "agent_usage_stats": {
        "url": "{base_url}/app/rest/builds?locator=agent:(id:{agent_id})"
        "&fields=build(id:{build_id},buildTypeId:{build_conf})",
        "name": "build agent usage statistics",
    },
    "test_occurrences": {
        "url": "{base_url}/app/rest/testOccurrences?locator=build:{build_id}",
        "name": "build test occurrences",
    },
    "build_problems": {
        "url": "{base_url}/app/rest/problemOccurrences?locator=build:(id:{build_id})",
        "name": "build problem occurrences",
    },
}

DEPLOYMENT_EVENT = {
    "timestamp": None,
    "event_type": "teamcity_deployment",
    "msg_title": "{instance_name} deployed to {host} {build_status}",
    "msg_text": "Build Number: {build_number}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ["deployment"],
}

BUILD_EVENT = {
    "timestamp": None,
    "event_type": "build",
    "msg_title": "Build for {instance_name} {build_status}",
    "msg_text": "Build Number: {build_number}\nDeployed To: {host}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ["build"],
}


def construct_event(is_deployment, instance_name, host, new_build, tags):
    build_id = new_build['id']
    build_number = new_build['number']
    build_tags = ['build_id:{}'.format(build_id), 'build_number:{}'.format(build_number)]
    tags.append(build_tags)
    if is_deployment:
        build_status = EVENT_STATUS_MAP.get(new_build['status'])
        teamcity_event = deepcopy(DEPLOYMENT_EVENT)
        teamcity_event['timestamp'] = int(time.time())
        teamcity_event['msg_title'] = teamcity_event['msg_title'].format(
            instance_name=instance_name, host=host, build_status=build_status
        )
        teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
            build_number=new_build['number'], build_webUrl=new_build['webUrl']
        )
        teamcity_event['host'] = host
    else:
        build_status = EVENT_STATUS_MAP.get(new_build['status'])
        teamcity_event = deepcopy(BUILD_EVENT)
        teamcity_event['timestamp'] = int(time.time())
        teamcity_event['msg_title'] = teamcity_event['msg_title'].format(
            instance_name=instance_name, build_status=build_status
        )
        teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
            build_number=new_build['number'], host=host, build_webUrl=new_build['webUrl']
        )
        teamcity_event['host'] = host

    teamcity_event['tags'].extend(tags)

    return teamcity_event


def get_response(check, resource, **kwargs):
    resource_url = RESOURCE_URL_MAP[resource]["url"].format(**kwargs)
    resource_name = RESOURCE_URL_MAP[resource]["name"]

    try:
        resp = check.http.get(resource_url)
        resp.raise_for_status()

        json_payload = resp.json()

        if not json_payload.get("count") or json_payload["count"] == 0:
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


class BuildConfigCache(object):
    def __init__(self):
        self._content = {}

    def set_build_config(self, build_type_id):
        if not self._content.get(build_type_id):
            self._content[build_type_id] = {"builds": set()}

    def get_build_config(self, build_type_id):
        if self._content.get(build_type_id):
            return self._content[build_type_id]

    def set_last_build_id(self, build_type_id, build_id, build_number):
        self._content[build_type_id]['last_build_ids'] = {'id': build_id, 'number': build_number}

    def get_last_build_id(self, build_type_id):
        if self._content.get(build_type_id):
            return self._content[build_type_id]["last_build_ids"]
