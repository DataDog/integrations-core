# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

NEW_BUILD_URL = (
    "{server}/{auth_type}/app/rest/builds/?locator=buildType:{build_conf},"
    "sinceBuild:id:{since_build},status:{event_status}"
)

LAST_BUILD_URL = "{server}/{auth_type}/app/rest/builds/?locator=buildType:{build_conf},count:1"

EVENT_STATUSES = ['SUCCESS', 'FAILURE']

DEPLOYMENT_EVENT = {
    "timestamp": int(time.time()),
    "event_type": "teamcity_deployment",
    "msg_title": "{instance_name} deployed to {host}",
    "msg_text": "Build Number: {build_number}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ['deployment'],
}

BUILD_EVENT = {
    "timestamp": int(time.time()),
    "event_type": "build",
    "msg_title": "Build for {instance_name} successful",
    "msg_text": "Build Number: {build_number}\nDeployed To: {host}\n\nMore Info: {build_webUrl}",
    "source_type_name": "teamcity",
    "host": None,
    "tags": ['build'],
}


def construct_event(is_deployment, instance_name, host, new_build, event_tags):
    if is_deployment:
        teamcity_event = DEPLOYMENT_EVENT
        teamcity_event['msg_title'] = teamcity_event['msg_title'].format(instance_name=instance_name, host=host)
        teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
            build_number=new_build['number'], build_webUrl=new_build['webUrl']
        )
        teamcity_event['host'] = host
    else:
        teamcity_event = BUILD_EVENT
        teamcity_event['msg_title'] = teamcity_event['msg_title'].format(instance_name=instance_name)
        teamcity_event['msg_text'] = teamcity_event['msg_text'].format(build_number=new_build['number'], host=host, build_webUrl=new_build["webUrl"])
        teamcity_event['host'] = host

    if event_tags:
        teamcity_event['tags'].append(event_tags)

    return teamcity_event
