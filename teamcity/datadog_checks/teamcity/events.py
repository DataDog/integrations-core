# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import requests

from datadog_checks.base import is_affirmative

NEW_BUILD_URL_SUCCESS = (
    "{server}/guestAuth/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},status:SUCCESS"
)
LAST_BUILD_URL = "{server}/guestAuth/app/rest/builds/?locator=buildType:{build_conf},count:1"

NEW_BUILD_URL_AUTHENTICATED_SUCCESS = (
    "{server}/httpAuth/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},status:SUCCESS"
)
LAST_BUILD_URL_AUTHENTICATED = "{server}/httpAuth/app/rest/builds/?locator=buildType:{build_conf},count:1"


def _initialize_if_required(self, instance_name, server, build_conf, basic_http_authentication):
    # Already initialized
    if instance_name in self.last_build_ids:
        return

    self.log.debug("Initializing %s", instance_name)

    if basic_http_authentication:
        build_url = LAST_BUILD_URL_AUTHENTICATED.format(server=server, build_conf=build_conf)
    else:
        build_url = LAST_BUILD_URL.format(server=server, build_conf=build_conf)
    try:
        resp = self.http.get(build_url)
        resp.raise_for_status()

        self.last_build_id = resp.json().get("build")[0].get("id")
    except requests.exceptions.HTTPError:
        if resp.status_code == 401:
            self.log.error("Access denied. You must enable guest authentication")
        self.log.error(
            "Failed to retrieve last build ID with code %s for instance '%s'", resp.status_code, instance_name
        )
        raise
    except Exception:
        self.log.exception("Unhandled exception to get last build ID for instance '%s'", instance_name)
        raise

    self.log.debug("Last build id for instance %s is %s.", instance_name, self.last_build_id)
    self.last_build_ids[instance_name] = self.last_build_id


def _build_and_send_event(self, new_build, instance_name, is_deployment, host, tags):
    self.log.debug("Found new build with id %s, saving and alerting.", new_build["id"])
    self.last_build_ids[instance_name] = new_build["id"]

    event_dict = {"timestamp": int(time.time()), "source_type_name": "teamcity", "host": host, "tags": []}
    if is_deployment:
        event_dict["event_type"] = "teamcity_deployment"
        event_dict["msg_title"] = "{} deployed to {}".format(instance_name, host)
        event_dict["msg_text"] = "Build Number: {}\n\nMore Info: {}".format(new_build["number"], new_build["webUrl"])
        event_dict["tags"].append("deployment")
    else:
        event_dict["event_type"] = "build"
        event_dict["msg_title"] = "Build for {} successful".format(instance_name)

        event_dict["msg_text"] = "Build Number: {}\nDeployed To: {}\n\nMore Info: {}".format(
            new_build["number"], host, new_build["webUrl"]
        )
        event_dict["tags"].append("build")

    if tags:
        event_dict["tags"].extend(tags)

    self.event(event_dict)


def collect_events(self, instance):
    instance_name = instance.get("name")
    if instance_name is None:
        raise Exception("Each instance must have a unique name")

    server = instance.get("server")
    if server is None:
        raise Exception("Each instance must have a server")

    server = self.base_url

    build_conf = instance.get("build_configuration")
    if build_conf is None:
        raise Exception("Each instance must have a build configuration")

    host = instance.get("host_affected") or self.hostname
    tags = instance.get("tags")
    is_deployment = is_affirmative(instance.get("is_deployment", False))
    basic_http_authentication = is_affirmative(instance.get("basic_http_authentication", False))

    _initialize_if_required(self, instance_name, server, build_conf, basic_http_authentication)

    # Look for new successful builds
    if basic_http_authentication:
        new_build_url = NEW_BUILD_URL_AUTHENTICATED_SUCCESS.format(
            server=server, build_conf=build_conf, since_build=self.last_build_ids[instance_name]
        )
    else:
        new_build_url = NEW_BUILD_URL_SUCCESS.format(
            server=server, build_conf=build_conf, since_build=self.last_build_ids[instance_name]
        )

    try:
        resp = self.http.get(new_build_url)
        resp.raise_for_status()

        new_builds = resp.json()

        if new_builds["count"] == 0:
            self.log.debug("No new builds found.")
        else:
            _build_and_send_event(new_builds["build"][0], instance_name, is_deployment, host, tags)
    except requests.exceptions.HTTPError:
        self.log.exception("Couldn't fetch last build, got code %s", resp.status_code)
        raise
    except Exception:
        self.log.exception("Couldn't fetch last build, unhandled exception")
        raise
