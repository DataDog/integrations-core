# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
import time
from collections import OrderedDict
from copy import deepcopy

from six import PY2

if PY2:
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

import requests

from .constants import BUILD_EVENT, DEPLOYMENT_EVENT, RESOURCE_URL_MAP, STATUS_MAP


def match(item, pattern_model):
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
        return dict.fromkeys((item for item in items if item not in excluded_items), None)
    else:

        filtered_items = {}
        for include_pattern in include_patterns:
            filtered_items.update(
                dict.fromkeys(
                    (item for item in items if item not in excluded_items and match(item, include_pattern)),
                    include_pattern,
                )
            )
        return filtered_items


def filter_items(items, key, default_limit, default_include, default_exclude, config=None):
    config = config if config else {}
    config_key = dict(config.get(key, config))
    limit = config_key.get('limit', default_limit)
    include_patterns = config_key.get('include', default_include)
    exclude_patterns = config_key.get('exclude', default_exclude)
    filtered_items = filter_list(items, include_patterns, exclude_patterns)
    # TODO: Use plain dict when we drop Python 2 support.
    ordered_items = OrderedDict(list(filtered_items.items())[:limit])
    reached_limit = len(ordered_items) < len(filtered_items)
    return ordered_items, reached_limit


def filter_projects(check, projects_list):
    return filter_items(
        items=projects_list,
        key='projects',
        config=check.instance,
        default_limit=check.default_projects_limit,
        default_include=None,
        default_exclude=None,
    )


def filter_build_configs(check, build_configs_list, project_pattern, config):
    return filter_items(
        items=build_configs_list,
        key=project_pattern,
        config=config,
        default_limit=check.default_build_configs_limit,
        default_include=check.global_build_configs_include,
        default_exclude=check.global_build_configs_exclude,
    )


def construct_event(check, new_build, build_config_type):
    """
    Construct event based on build status.
    """
    build_id = new_build['id']
    build_number = new_build['number']
    build_config = new_build['buildTypeId']
    instance_name = check.instance_name if check.instance_name else build_config
    build_status = STATUS_MAP.get(new_build['status']).get('msg_title', '')
    alert_type = STATUS_MAP.get(new_build['status']).get('alert_type', '')
    event_tags = deepcopy(check.build_tags)
    event_tags.extend(['build_id:{}'.format(build_id), 'build_number:{}'.format(build_number)])

    if check.is_deployment or build_config_type == 'deployment':
        teamcity_event = deepcopy(DEPLOYMENT_EVENT)
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
        elif json_payload.get("count", 0) == 0:
            check.log.debug("No results found for resource %s url: %s", resource_name, resource_url)
            return {}
        else:
            check.log.debug("Results found for resource %s url: %s", resource_name, resource_url)
            return json_payload
    except requests.exceptions.HTTPError:
        if resp.status_code in (401, 403):
            check.log.error("Access denied. Enable guest authentication or check user permissions.")
        check.log.exception("Couldn't fetch resource %s, got code %s", resource_name, resp.status_code)
        raise
    except Exception as e:
        check.log.exception("Couldn't fetch resource %s, unhandled exception %s", resource_name, str(e))
        raise


def sanitize_server_url(url):
    parsed_url = urlparse(url)
    if parsed_url.password:
        sanitized_endpoint = "{}://{}".format(parsed_url.scheme, parsed_url.hostname)
        if parsed_url.port:
            sanitized_endpoint += ":{}".format(parsed_url.port)
        return sanitized_endpoint
    return url


def normalize_server_url(server):
    """
    Check if the server URL starts with an HTTP or HTTPS scheme, fall back to http if not present
    """
    return server if server.startswith(("http://", "https://")) else "http://{}".format(server)
