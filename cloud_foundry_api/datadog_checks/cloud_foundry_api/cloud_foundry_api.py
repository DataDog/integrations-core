# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from typing import Any, Dict

from dateutil import parser
from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import Event


class CloudFoundryApiCheck(AgentCheck):
    SOURCE_TYPE_NAME = "CloudFoundry"
    __NAMESPACE__ = "cloud_foundry_api"

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
        if self._oauth_token is not None and self._token_expiration > int(time.time()):
            return
        self.log.info("Refreshing access token")
        res = self.http.get(
            f"{self._uaa_url}/oauth/token",
            auth=(self._client_id, self._client_secret),
            params={"grant_type": "client_credentials"},
        )
        try:
            res.raise_for_status()
            payload = res.json()
            if "access_token" in payload and "expires_in" in payload:
                self._oauth_token = payload["access_token"]
                self._token_expiration = int(time.time()) + payload["expires_in"]
                return
            self.log.error("Could not find access token and expiration in payload: %s", payload)
        except HTTPError as e:
            self.log.error("Error authenticating to the UAA server: %s - %s", e, res.text)
            raise
        except ValueError as e:
            self.log.error("Error decoding response from the UAA server: %s - %s", e, res.text)
            raise

    def get_events_v2(self):
        events = {}
        scroll = True
        params = {
            "q": f"type IN {self._event_filter}",
            "results-per-page": min(self._per_page, 100),
            "order-direction": "desc",
            "order-by": "timestamp",
        }
        headers = {"Authorization": f"Bearer {self._oauth_token}"}
        res = self.http.get(f"{self._api_url}/v2/events", params=params, headers=headers)
        while scroll:
            try:
                res.raise_for_status()
                payload = res.json()
            except HTTPError as e:
                self.log.error("Error querying list of events: %s - %s", e, res.text)
                break
            except ValueError as e:
                self.log.error("Error decoding response from the UAA server: %s - %s", e, res.text)
                break
            # Collect events
            for v2_event in payload.get("resources", []):
                event_ts = int(parser.isoparse(v2_event["entity"]["timestamp"]).timestamp())
                event_guid = v2_event["metadata"]["guid"]
                # Stop going through events if we've reached one we've already fetched or if we went back in time enough
                if event_guid == self._last_event_guid or int(time.time()) - event_ts > 600:
                    scroll = False
                    break
                if event_ts > self._last_event_ts:
                    self._last_event_guid = event_guid
                    self._last_event_ts = event_ts
                tags = [
                    f"event_type:{v2_event['entity']['type']}",
                    f"{v2_event['entity']['actee_type']}_name:{v2_event['entity']['actee_name']}",
                    f"{v2_event['entity']['actee_type']}_guid:{v2_event['entity']['actee']}",
                    f"{v2_event['entity']['actor_type']}_name:{v2_event['entity']['actor_name']}",
                    f"{v2_event['entity']['actor_type']}_guid:{v2_event['entity']['actor']}",
                    f"space_guid:{v2_event['entity']['space_guid']}",
                    f"org_guid:{v2_event['entity']['organization_guid']}",
                ]
                dd_event = {
                    "source_type_name": CloudFoundryApiCheck.SOURCE_TYPE_NAME,
                    "event_type": v2_event["entity"]["type"],
                    "timestamp": event_ts,
                    "msg_title": f"Event {v2_event['entity']['type']} happened for {v2_event['entity']['actee_type']} "
                    f"{v2_event['entity']['actee_name']}",
                    "msg_text": f"Triggered by {v2_event['entity']['actor_type']} {v2_event['entity']['actor_name']}",
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
            res = self.http.get(f"{self._api_url}{next_url}", headers=headers)
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
            # res = self.http.get(f"{self._api_url}/v3/audit_events")
            pass
        else:
            self.log.error("Unknown api version `%s`, choose between `v2` and `v3`", self._api_version)

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        events = self.get_events()
        self.count("events.count", len(events))
        for event in events.values():
            self.event(event)
