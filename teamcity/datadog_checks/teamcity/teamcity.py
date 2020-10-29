# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time

import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import _is_affirmative


class TeamCityCheck(AgentCheck):

    NEW_BUILD_URL = (
        "{server}/guestAuth/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},status:SUCCESS"
    )
    LAST_BUILD_URL = "{server}/guestAuth/app/rest/builds/?locator=buildType:{build_conf},count:1"

    NEW_BUILD_URL_AUTHENTICATED = (
        "{server}/httpAuth/app/rest/builds/?locator=buildType:{build_conf},sinceBuild:id:{since_build},status:SUCCESS"
    )
    LAST_BUILD_URL_AUTHENTICATED = "{server}/httpAuth/app/rest/builds/?locator=buildType:{build_conf},count:1"

    HTTP_CONFIG_REMAPPER = {
        'ssl_validation': {'name': 'tls_verify'},
        'headers': {'name': 'headers', 'default': {"Accept": "application/json"}},
    }

    def __init__(self, name, init_config, instances):
        super(TeamCityCheck, self).__init__(name, init_config, instances)
        # Keep track of last build IDs per instance
        self.last_build_ids = {}

    def _initialize_if_required(self, instance_name, server, build_conf, basic_http_authentication):
        # Already initialized
        if instance_name in self.last_build_ids:
            return

        self.log.debug("Initializing %s", instance_name)

        if basic_http_authentication:
            build_url = self.LAST_BUILD_URL_AUTHENTICATED.format(server=server, build_conf=build_conf)
        else:
            build_url = self.LAST_BUILD_URL.format(server=server, build_conf=build_conf)
        try:
            resp = self.http.get(build_url)
            resp.raise_for_status()

            last_build_id = resp.json().get("build")[0].get("id")
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

        self.log.debug("Last build id for instance %s is %s.", instance_name, last_build_id)
        self.last_build_ids[instance_name] = last_build_id

    def _build_and_send_event(self, new_build, instance_name, is_deployment, host, tags):
        self.log.debug("Found new build with id %s, saving and alerting.", new_build["id"])
        self.last_build_ids[instance_name] = new_build["id"]

        event_dict = {"timestamp": int(time.time()), "source_type_name": "teamcity", "host": host, "tags": []}
        if is_deployment:
            event_dict["event_type"] = "teamcity_deployment"
            event_dict["msg_title"] = "{} deployed to {}".format(instance_name, host)
            event_dict["msg_text"] = "Build Number: {}\n\nMore Info: {}".format(
                new_build["number"], new_build["webUrl"]
            )
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

    def _normalize_server_url(self, server):
        """
        Check if the server URL starts with a HTTP or HTTPS scheme, fall back to http if not present
        """
        server = server if server.startswith(("http://", "https://")) else "http://{}".format(server)
        return server

    def check(self, _):
        instance_name = self.instance.get("name")
        if instance_name is None:
            raise Exception("Each instance must have a unique name")

        server = self.instance.get("server")
        if server is None:
            raise Exception("Each instance must have a server")

        # Check the server URL for HTTP or HTTPS designation,
        #   fall back to http:// if no scheme present (allows for backwards compatibility).
        server = self._normalize_server_url(server)

        build_conf = self.instance.get("build_configuration")
        if build_conf is None:
            raise Exception("Each instance must have a build configuration")

        host = self.instance.get("host_affected") or self.hostname
        tags = self.instance.get("tags")
        is_deployment = _is_affirmative(self.instance.get("is_deployment", False))
        basic_http_authentication = _is_affirmative(self.instance.get("basic_http_authentication", False))

        self._initialize_if_required(instance_name, server, build_conf, basic_http_authentication)

        # Look for new successful builds
        if basic_http_authentication:
            new_build_url = self.NEW_BUILD_URL_AUTHENTICATED.format(
                server=server, build_conf=build_conf, since_build=self.last_build_ids[instance_name]
            )
        else:
            new_build_url = self.NEW_BUILD_URL.format(
                server=server, build_conf=build_conf, since_build=self.last_build_ids[instance_name]
            )

        try:
            resp = self.http.get(new_build_url)
            resp.raise_for_status()

            new_builds = resp.json()

            if new_builds["count"] == 0:
                self.log.debug("No new builds found.")
            else:
                self._build_and_send_event(new_builds["build"][0], instance_name, is_deployment, host, tags)
        except requests.exceptions.HTTPError:
            self.log.exception("Couldn't fetch last build, got code %s", resp.status_code)
            raise
        except Exception:
            self.log.exception("Couldn't fetch last build, unhandled exception")
            raise
