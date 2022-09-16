# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import time
from copy import deepcopy

import requests

from datadog_checks.base import ConfigurationError

from .constants import BUILD_EVENT, DEPLOYMENT_EVENT, EVENT_STATUS_MAP, RESOURCE_URL_MAP


def construct_build_configs_filter(check):
    """
    Construct build configuration filter
    """
    excluded_build_configs = set()
    included_build_configs = set()
    for project in check.monitored_build_configs:
        config = check.monitored_build_configs.get(project)
        # collect all build configs in project
        if isinstance(config, dict):
            exclude_list = config.get('exclude', [])
            include_list = config.get('include', [])
            if exclude_list:
                excluded_build_configs.update(exclude_list)
            if include_list:
                for include_bc in include_list:
                    if include_bc not in excluded_build_configs:
                        included_build_configs.update([include_bc])
        elif config is None:
            continue
        else:
            raise ConfigurationError(
                "`project` must be either an empty mapping to collect all build configurations in the project"
                "or a mapping of keys `include` and/or `exclude` lists of build configurations."
            )
    return excluded_build_configs, included_build_configs


def should_include_build_config(check, build_config):
    """
    Return `True` if the build_config is included, otherwise `False`
    """
    exclude_filter, include_filter = construct_build_configs_filter(check)
    include_match = False
    exclude_match = False
    # If no filters configured, include everything
    if not exclude_filter and not include_filter:
        return True
    if exclude_filter:
        for pattern in exclude_filter:
            if re.search(re.compile(pattern), build_config):
                exclude_match = True
    if include_filter:
        for pattern in include_filter:
            if re.search(re.compile(pattern), build_config):
                include_match = True

    # Include everything except in excluded_bc
    if exclude_filter and not include_filter:
        return not exclude_match
    # Include only what's defined in included_bc
    if include_filter and not exclude_filter:
        return include_match
    # If both include and exclude filters are configured
    if include_filter and exclude_filter:
        # If filter overlap or in neither filter, exclude
        if (include_match and exclude_match) or (not include_match and not exclude_match):
            return False
        # Only matches include filter, include
        if include_match and not exclude_match:
            return include_match
        # Only matches exclude filter, exclude
        if exclude_match and not include_match:
            return not exclude_match
    return True


def construct_event(check, new_build):
    """
    Construct event based on build status.
    """
    instance_name = check.instance_name
    build_id = new_build['id']
    build_number = new_build['number']
    build_config = new_build['buildTypeId']
    build_status = EVENT_STATUS_MAP.get(new_build['status'])
    event_tags = deepcopy(check.build_tags)
    event_tags.extend(['build_id:{}'.format(build_id), 'build_number:{}'.format(build_number)])

    if not check.instance_name:
        instance_name = build_config

    if check.is_deployment:
        teamcity_event = deepcopy(DEPLOYMENT_EVENT)
        teamcity_event['tags'].append('type:deployment')
    else:
        teamcity_event = deepcopy(BUILD_EVENT)
        teamcity_event['tags'].append('build')

    teamcity_event['timestamp'] = int(time.time())
    teamcity_event['msg_title'] = teamcity_event['msg_title'].format(
        instance_name=instance_name, host=check.host, build_status=build_status
    )
    teamcity_event['msg_text'] = teamcity_event['msg_text'].format(
        build_number=new_build['number'], host=check.host, build_webUrl=new_build['webUrl']
    )
    teamcity_event['host'] = check.host
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
