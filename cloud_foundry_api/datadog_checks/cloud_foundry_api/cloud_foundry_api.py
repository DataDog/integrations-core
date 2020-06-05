# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from typing import Any, Dict

from dateutil import parser
from requests.exceptions import HTTPError, RequestException

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import Event


class CloudFoundryApiCheck(AgentCheck):
    __NAMESPACE__ = "cloud_foundry_api"

    SOURCE_TYPE_NAME = "Cloud Foundry"
    MAX_LOOKBACK_SECONDS = 600
    TOCKEN_EXPIRATION_BUFFER = 300

    def __init__(self, name, init_config, instances):
        super(CloudFoundryApiCheck, self).__init__(name, init_config, instances)

        self._api_url = self.instance.get("api_url")
        self._uaa_url = self.instance.get("uaa_url")
        self._client_id = self.instance.get("client_id")
        self._client_secret = self.instance.get("client_id")
        self._api_version = self.instance.get("api_version", "v3")
        self._event_filter = ",".join(self.instance.get("event_filter", []))
        self._tags = self.instance.get("tags", [])
        self._per_page = self.instance.get("results_per_page", 2000)
        self._last_event_guid = ""
        self._last_event_ts = 0
        self._oauth_token = None
        self._token_expiration = 0

    def get_oauth_token(self):
        # type: () -> str
        if (
            self._oauth_token is not None
            and self._token_expiration - CloudFoundryApiCheck.TOCKEN_EXPIRATION_BUFFER > int(time.time())
        ):
            return
        self.log.info("Refreshing access token")
        try:
            res = self.http.get(
                "{}/oauth/token".format(self._uaa_url),
                auth=(self._client_id, self._client_secret),
                params={"grant_type": "client_credentials"},
            )
        except RequestException:
            self.log.exception("Error connecting to the UAA server")
            raise
        try:
            res.raise_for_status()
        except HTTPError:
            self.log.exception("Error authenticating to the UAA server: response: %s", res.text)
            raise
        try:
            payload = res.json()
        except ValueError:
            self.log.exception("Error decoding response from the UAA server: response: %s", res.text)
            raise

        self._oauth_token = payload["access_token"]
        self._token_expiration = int(time.time()) + payload["expires_in"]

    def get_events_v2(self):
        events = {}
        scroll = True
        params = {
            "q": "type IN {}".format(self._event_filter),
            "results-per-page": min(self._per_page, 100),
            "page": 1,
            "order-direction": "desc",
            "order-by": "timestamp",
        }
        headers = {"Authorization": "Bearer {}".format(self._oauth_token)}
        while scroll:
            try:
                res = self.http.get("{}/v2/events".format(self._api_url), params=params, headers=headers)
            except RequestException:
                self.log.exception("Error connecting to the Cloud Controller API")
                break
            try:
                res.raise_for_status()
            except HTTPError:
                self.log.exception("Error querying list of events: response %s", res.text)
                break
            try:
                payload = res.json()
            except ValueError:
                self.log.error("Error decoding response from the Cloud Controller API: response %s", res.text)
                break
            # Collect events
            for v2_event in payload.get("resources", []):
                event_ts = int(parser.isoparse(v2_event["entity"]["timestamp"]).timestamp())
                event_guid = v2_event["metadata"]["guid"]
                # Stop going through events if we've reached one we've already fetched or if we went back in time enough
                if (
                    event_guid == self._last_event_guid
                    or int(time.time()) - event_ts > CloudFoundryApiCheck.MAX_LOOKBACK_SECONDS
                ):
                    scroll = False
                    break
                # Store the event at which we want to stop on the next check run: the most recent of the current run
                if event_ts > self._last_event_ts:
                    self._last_event_guid = event_guid
                    self._last_event_ts = event_ts
                tags = [
                    "event_type:{}".format(v2_event["entity"]["type"]),
                    "{}_name:{}".format(v2_event["entity"]["actee_type"], v2_event["entity"]["actee_name"]),
                    "{}_guid:{}".format(v2_event["entity"]["actee_type"], v2_event["entity"]["actee"]),
                    "{}_name:{}".format(v2_event["entity"]["actor_type"], v2_event["entity"]["actor_name"]),
                    "{}_guid:{}".format(v2_event["entity"]["actor_type"], v2_event["entity"]["actor"]),
                    "space_guid:{}".format(v2_event["entity"]["space_guid"]),
                    "org_guid:{}".format(v2_event["entity"]["organization_guid"]),
                ]
                dd_event = {
                    "source_type_name": CloudFoundryApiCheck.SOURCE_TYPE_NAME,
                    "event_type": v2_event["entity"]["type"],
                    "timestamp": event_ts,
                    "msg_title": "Event {} happened for {} {}".format(
                        v2_event["entity"]["type"], v2_event["entity"]["actee_type"], v2_event["entity"]["actee_name"]
                    ),
                    "msg_text": "Triggered by {} {}".format(
                        v2_event["entity"]["actor_type"], v2_event["entity"]["actor_name"]
                    ),
                    "priority": "normal",
                    "tags": tags,
                }
                # Make sure we don't send duplicate events in case the pagination gets shifted by new events
                if event_guid not in events:
                    events[event_guid] = dd_event
            # Fetch next page if any
            next_url = payload.get("next_url")
            if not next_url or not scroll:
                break
            params["page"] += 1
        return events

    def get_events(self):
        # type: () -> Dict[str: Event]
        self.get_oauth_token()
        if self._api_version == "v2":
            return self.get_events_v2()
        elif self._api_version == "v3":
            # self.get_events_v3()
            # params = {
            #     "types": self._event_filter,
            #     "per_page": min(self._per_page, 5000),
            #     "order_by": "-created_at",
            # }
            # res = self.http.get("{}/v3/audit_events".format(self._api_url))
            pass
        else:
            self.log.error("Unknown api version `%s`, choose between `v2` and `v3`", self._api_version)

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        events = self.get_events()
        self.count("events.count", len(events))
        for event in events.values():
            self.event(event)
