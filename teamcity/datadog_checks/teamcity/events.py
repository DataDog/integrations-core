# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger

from .common import EVENT_STATUSES, LAST_BUILD_URL, NEW_BUILD_URL, construct_event


class TeamCityEvents(object):
    def __init__(self, instance, server_url, hostname, auth_type):
        self._last_build_ids = {}
        self.instance_name = instance.get('name')
        self.server_url = server_url
        self.host = hostname
        self.build_config = instance.get('build_configuration')
        self.event_tags = instance.get('tags')
        self.is_deployment = is_affirmative(instance.get("is_deployment", False))
        self.auth_type = auth_type
        self.log = get_check_logger()

    def _build_and_send_event(self, check, new_build, event_tags):
        self.log.debug("Found new build with id %s, saving and alerting.", new_build["id"])
        self._last_build_ids[self.instance_name] = new_build["id"]

        teamcity_event = construct_event(self.is_deployment, self.instance_name, self.host, new_build, event_tags)
        check.event(teamcity_event)

    def _construct_event_urls(self):
        event_urls = []

        for status in EVENT_STATUSES:
            event_urls.append(
                NEW_BUILD_URL.format(
                    server=self.server_url,
                    auth_type=self.auth_type,
                    build_conf=self.build_config,
                    since_build=self._last_build_ids[self.instance_name],
                    event_status=status,
                )
            )

        return event_urls

    def collect_events(self, check, last_build_ids):
        self._last_build_ids = last_build_ids
        new_build_urls = self._construct_event_urls()

        for url in new_build_urls:
            try:
                resp = check.http.get(url)
                resp.raise_for_status()
                new_builds = resp.json()

                if new_builds["count"] == 0:
                    self.log.debug("No new builds found.")
                else:
                    self._build_and_send_event(check, new_builds["build"][0], self.event_tags)
            except requests.exceptions.HTTPError:
                self.log.exception("Couldn't fetch last build, got code %s", resp.status_code)
                raise
            except Exception:
                self.log.exception("Couldn't fetch last build, unhandled exception")
                raise
