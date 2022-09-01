# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from copy import deepcopy

from datadog_checks.base import AgentCheck

# BASE_URL = "{server}/{auth_type}/app/rest/"

NEW_BUILD_URL = (
    "{server}/{auth_type}/app/rest/builds/?locator=buildType:{build_conf}," "sinceBuild:id:{since_build},state:finished"
)

LAST_BUILD_URL = "{server}/{auth_type}/app/rest/builds/?locator=buildType:{build_conf},count:1"

BUILD_STATS_URL = "{server}/{auth_type}/app/rest/builds/buildType:{build_conf},buildId:{build_id}/statistics/"

TEST_OCCURRENCES_URL = "{server}/{auth_type}/app/rest/testOccurrences?locator=build:{build_id}"

BUILD_PROBLEM_OCCURRENCES_URL = "{server}/{auth_type}/app/rest/problemOccurrences?locator=build:(id:{build_id})"

EVENT_STATUS_MAP = {"SUCCESS": "successful", "FAILURE": "failed"}

SERVICE_CHECK_STATUS_MAP = {"SUCCESS": AgentCheck.OK, "FAILURE": AgentCheck.CRITICAL}

DEPLOYMENT_EVENT = {
    "timestamp": None,
    "event_type": "teamcity_deployment",
    "msg_title": "{instance_name} deployed to {host} {build_status}",
    "msg_text": "Build Number: {build_number}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ['deployment'],
}

BUILD_EVENT = {
    "timestamp": None,
    "event_type": "build",
    "msg_title": "Build for {instance_name} {build_status}",
    "msg_text": "Build Number: {build_number}\nDeployed To: {host}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ['build'],
}


def construct_event(is_deployment, instance_name, host, new_build, tags):
    build_id = new_build['id']
    build_number = new_build['number']
    build_tags = [f'build_id:{build_id}', f'build_number:{build_number}']
    tags.append(build_tags)
    if is_deployment:
        build_status = EVENT_STATUS_MAP.get(new_build["status"])
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
        build_status = EVENT_STATUS_MAP.get(new_build["status"])
        teamcity_event = deepcopy(BUILD_EVENT)
        teamcity_event['timestamp'] = int(time.time())
        teamcity_event['msg_title'] = teamcity_event['msg_title'].format(
            instance_name=instance_name, build_status=build_status
        )
        teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
            build_number=new_build['number'], host=host, build_webUrl=new_build["webUrl"]
        )
        teamcity_event['host'] = host

    teamcity_event['tags'].extend(tags)

    return teamcity_event
