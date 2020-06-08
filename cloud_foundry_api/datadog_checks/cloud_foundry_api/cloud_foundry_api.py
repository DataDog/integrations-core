# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from typing import Any, Callable, Dict

from requests.exceptions import HTTPError, RequestException

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import Event

from .constants import (
    API_SERVICE_CHECK_NAME,
    DEFAULT_PAGE_SIZE,
    MAX_LOOKBACK_SECONDS,
    MAX_PAGE_SIZE_V2,
    MAX_PAGE_SIZE_V3,
    TOCKEN_EXPIRATION_BUFFER,
    UAA_SERVICE_CHECK_NAME,
)
from .utils import parse_event_v2, parse_event_v3


class CloudFoundryApiCheck(AgentCheck):
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
        self._per_page = self.instance.get("results_per_page", DEFAULT_PAGE_SIZE)
        self._last_event_guid = ""
        self._last_event_ts = 0
        self._oauth_token = None
        self._token_expiration = 0

    def get_oauth_token(self):
        # type: () -> str
        if self._oauth_token is not None and self._token_expiration - TOCKEN_EXPIRATION_BUFFER > int(time.time()):
            return
        self.log.info("Refreshing access token")
        sc_tags = ["uaa_url:{}".format(self._uaa_url)]
        try:
            res = self.http.get(
                "{}/oauth/token".format(self._uaa_url),
                auth=(self._client_id, self._client_secret),
                params={"grant_type": "client_credentials"},
            )
        except RequestException:
            self.log.exception("Error connecting to the UAA server")
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise
        try:
            res.raise_for_status()
        except HTTPError:
            self.log.exception("Error authenticating to the UAA server: response: %s", res.text)
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise
        try:
            payload = res.json()
        except ValueError:
            self.log.exception("Error decoding response from the UAA server: response: %s", res.text)
            self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
            raise

        self._oauth_token = payload["access_token"]
        self._token_expiration = int(time.time()) + payload["expires_in"]
        self.service_check(UAA_SERVICE_CHECK_NAME, CloudFoundryApiCheck.OK, tags=sc_tags)

    def get_events_v2(self):
        # type: () -> Dict[str, Event]
        params = {
            "q": "type IN {}".format(self._event_filter),
            "results-per-page": min(self._per_page, MAX_PAGE_SIZE_V2),
            "page": 1,
            "order-direction": "desc",
            "order-by": "timestamp",
        }
        headers = {"Authorization": "Bearer {}".format(self._oauth_token)}
        url = "{}/v2/events".format(self._api_url)
        return self.scroll_pages(url, params, headers, parse_event_v2)

    def get_events_v3(self):
        # type: () -> Dict[str, Event]
        params = {
            "types": self._event_filter,
            "per_page": min(self._per_page, MAX_PAGE_SIZE_V3),
            "order_by": "-created_at",
        }
        headers = {"Authorization": "Bearer {}".format(self._oauth_token)}
        url = "{}/v3/audit_events".format(self._api_url)
        return self.scroll_pages(url, params, headers, parse_event_v3)

    def scroll_pages(self, url, params, headers, event_parser):
        # type: (str, Dict[str, Any], Dict[str, str], Callable) -> Dict[str, Event]
        page = 1
        events = {}
        scroll = True
        sc_tags = ["api_url:{}".format(self._api_url)]
        while scroll:
            params["page"] = page
            try:
                res = self.http.get(url, params=params, headers=headers)
            except RequestException:
                self.log.exception("Error connecting to the Cloud Controller API")
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                break
            try:
                res.raise_for_status()
            except HTTPError:
                self.log.exception("Error querying list of events: response %s", res.text)
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                break
            try:
                payload = res.json()
            except ValueError:
                self.log.error("Error decoding response from the Cloud Controller API: response %s", res.text)
                self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.CRITICAL, tags=sc_tags)
                break

            for cf_event in payload.get("resources", []):
                dd_event, event_guid, event_ts = event_parser(cf_event)
                # Stop going through events if we've reached one we've already fetched or if we went back in time enough
                if event_guid == self._last_event_guid or int(time.time()) - event_ts > MAX_LOOKBACK_SECONDS:
                    scroll = False
                    break
                # Store the event at which we want to stop on the next check run: the most recent of the current run
                if event_ts > self._last_event_ts:
                    self._last_event_guid = event_guid
                    self._last_event_ts = event_ts
                # Make sure we don't send duplicate events in case the pagination gets shifted by new events
                if event_guid not in events:
                    events[event_guid] = dd_event
            # Fetch next page if any
            next_url = payload.get("next_url")
            if not next_url or not scroll:
                break
            page += 1
        self.service_check(API_SERVICE_CHECK_NAME, CloudFoundryApiCheck.OK, tags=sc_tags)
        return events

    def get_events(self):
        # type: () -> Dict[str, Event]
        self.get_oauth_token()
        if self._api_version == "v2":
            return self.get_events_v2()
        elif self._api_version == "v3":
            return self.get_events_v3()

        self.log.error("Unknown api version `%s`, choose between `v2` and `v3`", self._api_version)
        return {}

    def check(self, _):
        # type: (Dict[str, Any]) -> None
        events = self.get_events()
        self.count("events.count", len(events))
        for event in events.values():
            self.event(event)
