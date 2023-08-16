# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

SERVICE_CHECK_BUILD_STATUS = 'build.status'
SERVICE_CHECK_BUILD_PROBLEMS = 'build.problems'
SERVICE_CHECK_TEST_RESULTS = 'test.results'
SERVICE_CHECK_OPENMETRICS = 'teamcity.openmetrics.health'

DEFAULT_BUILD_CONFIGS_LIMIT = 5
DEFAULT_PROJECTS_LIMIT = 5
DEFAULT_PROJECTS_REFRESH_INTERVAL = 3600

STATUS_MAP = {
    "SUCCESS": {"check_status": AgentCheck.OK, "msg_title": "successful", "alert_type": "success"},
    "FAILURE": {"check_status": AgentCheck.CRITICAL, "msg_title": "failed", "alert_type": "error"},
    "UNKNOWN": {"check_status": AgentCheck.UNKNOWN},
    "NORMAL": {"check_status": AgentCheck.OK},
    "WARNING": {"check_status": AgentCheck.WARNING},
    "ERROR": {"check_status": AgentCheck.CRITICAL},
}

RESOURCE_URL_MAP = {
    "projects": "{base_url}/app/rest/projects",
    "build_configs": "{base_url}/app/rest/buildTypes?locator=project(id:{project_id})",
    "build_config": "{base_url}/app/rest/buildTypes/id:{build_conf}",
    "new_builds": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},"
    "state:finished,defaultFilter:false",
    "last_build": "{base_url}/app/rest/builds/?locator=buildType:{build_conf},project:{project_id},count:1",
    "build_stats": "{base_url}/app/rest/builds/buildId:{build_id}/statistics",
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
