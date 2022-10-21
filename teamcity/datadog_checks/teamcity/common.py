# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import time
from collections import OrderedDict
from copy import deepcopy

import requests

from .constants import BUILD_EVENT, DEPLOYMENT_EVENT, RESOURCE_URL_MAP, STATUS_MAP


def match(item: str, pattern_model) -> bool:
    if isinstance(pattern_model, str):
        return re.search(pattern_model, item)
    if isinstance(pattern_model, dict) and len(pattern_model) == 1:
        return re.search(list(pattern_model.keys())[0], item)
    elif isinstance(pattern_model, list):
        return any(match(item, pattern) for pattern in pattern_model)
    return False


def filter_list(items, include_patterns, exclude_patterns):
    excluded_items = [item for item in items if match(item, exclude_patterns) if exclude_patterns]
    if not include_patterns:
        return {item: None for item in items if item not in excluded_items}
    else:
        filtered_items = {}
        for include_pattern in include_patterns:
            filtered_items = filtered_items | {
                item: include_pattern for item in items if item not in excluded_items and match(item, include_pattern)
            }
        return filtered_items


def filter_items(
    items, key: str, config: dict, default_limit: int, default_include: list, default_exclude: list
) -> OrderedDict:
    config_key = dict(config.get(key, {}))
    limit = config_key.get('build_configs_limit', default_limit)
    include_patterns = config_key.get('include', default_include)
    exclude_patterns = config_key.get('exclude', default_exclude)
    filtered_items = filter_list(items, include_patterns, exclude_patterns)
    return OrderedDict(list(filtered_items.items())[0:limit])


def should_include_build_config(check, build_config, project_id):
    """
    Return `True` if the build_config is included, otherwise `False`
    """
    return filter_items(
        [build_config],
        project_id,
        check.monitored_projects,
        check.default_build_configs_limit,
        check.global_build_configs_include,
        check.global_build_configs_exclude,
    )


def construct_event(check, new_build):
    """
    Construct event based on build status.
    """
    instance_name = check.instance_name
    build_id = new_build['id']
    build_number = new_build['number']
    build_config = new_build['buildTypeId']
    build_status = STATUS_MAP.get(new_build['status'])['msg_title']
    alert_type = STATUS_MAP.get(new_build['status'])['alert_type']
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
    teamcity_event['alert_type'] = alert_type
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
        if resource == 'build_config' or resource == 'teamcity_server_details':
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
    except Exception as e:
        check.log.exception("Couldn't fetch resource %s, unhandled exception %s, %s", resource_name, str(e), resp)
        raise
